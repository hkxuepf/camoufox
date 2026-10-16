#import <Cocoa/Cocoa.h>
#import <objc/runtime.h>

typedef enum {
    LOCK_MODE_NONE = 0,
    LOCK_MODE_STRICT = 1,  // Mobile: completely fixed window size, no resize, no zoom, no full screen
    LOCK_MODE_CAP = 2      // Desktop: allowed to resize smaller, but strictly capped at targetW x targetH
} CamouLockMode;

static CamouLockMode g_lockMode = LOCK_MODE_NONE;
static int g_targetW = 0;
static int g_targetH = 0;

static void Swizzle(Class cls, SEL orig, SEL swiz) {
    Method origMethod = class_getInstanceMethod(cls, orig);
    Method swizMethod = class_getInstanceMethod(cls, swiz);
    if (origMethod && swizMethod) {
        method_exchangeImplementations(origMethod, swizMethod);
    }
}

@interface NSWindow (CamouLock)
@end

@implementation NSWindow (CamouLock)

- (void)camou_zoom:(id)sender {
    if (g_lockMode == LOCK_MODE_STRICT) {
        NSLog(@"[CamouWindowLock] Blocked zoom in strict mode.");
        return;
    }
    if (g_lockMode == LOCK_MODE_CAP && g_targetW > 0 && g_targetH > 0) {
        // In desktop capped mode, zooming should only expand up to the target profile dimensions
        NSRect currentFrame = [self frame];
        NSScreen *screen = [self screen] ?: [NSScreen mainScreen];
        NSRect visible = screen ? [screen visibleFrame] : currentFrame;

        CGFloat maxAllowedW = MIN((CGFloat)g_targetW, visible.size.width);
        CGFloat maxAllowedH = MIN((CGFloat)g_targetH, visible.size.height);

        // If already maximized to capped size, toggle back to smaller size
        if (fabs(currentFrame.size.width - maxAllowedW) < 5.0 && fabs(currentFrame.size.height - maxAllowedH) < 5.0) {
            CGFloat restoredW = MAX(800.0, maxAllowedW * 0.75);
            CGFloat restoredH = MAX(600.0, maxAllowedH * 0.75);
            CGFloat newX = currentFrame.origin.x;
            CGFloat newY = currentFrame.origin.y + (currentFrame.size.height - restoredH);
            [self setFrame:NSMakeRect(newX, newY, restoredW, restoredH) display:YES animate:YES];
            return;
        }

        // Otherwise zoom to the capped maximum
        CGFloat newX = visible.origin.x + (visible.size.width - maxAllowedW) / 2.0;
        CGFloat newY = visible.origin.y + (visible.size.height - maxAllowedH) / 2.0;
        [self setFrame:NSMakeRect(newX, newY, maxAllowedW, maxAllowedH) display:YES animate:YES];
        return;
    }
    [self camou_zoom:sender];
}

- (void)camou_toggleFullScreen:(id)sender {
    if (g_lockMode == LOCK_MODE_STRICT || g_lockMode == LOCK_MODE_CAP) {
        NSLog(@"[CamouWindowLock] Blocked native fullscreen to prevent exceeding profile screen dimensions.");
        // If user requested fullscreen in desktop mode, simulate max zoom within profile bounds
        if (g_lockMode == LOCK_MODE_CAP) {
            [self camou_zoom:sender];
        }
        return;
    }
    [self camou_toggleFullScreen:sender];
}

- (void)camou_setStyleMask:(NSWindowStyleMask)styleMask {
    if (g_lockMode == LOCK_MODE_STRICT) {
        if ((styleMask & NSWindowStyleMaskTitled) && !(styleMask & NSWindowStyleMaskDocModalWindow)) {
            styleMask &= ~NSWindowStyleMaskResizable;
        }
    }
    [self camou_setStyleMask:styleMask];
}

- (void)camou_setMinSize:(NSSize)size {
    if (g_lockMode == LOCK_MODE_STRICT && g_targetW > 0 && g_targetH > 0 && (self.styleMask & NSWindowStyleMaskTitled)) {
        [self camou_setMinSize:NSMakeSize(g_targetW, g_targetH)];
    } else {
        [self camou_setMinSize:size];
    }
}

- (void)camou_setMaxSize:(NSSize)size {
    if (g_targetW > 0 && g_targetH > 0 && (self.styleMask & NSWindowStyleMaskTitled)) {
        [self camou_setMaxSize:NSMakeSize(g_targetW, g_targetH)];
    } else {
        [self camou_setMaxSize:size];
    }
}

- (void)camou_setFrame:(NSRect)frameRect display:(BOOL)displayFlag animate:(BOOL)animateFlag {
    if (g_targetW > 0 && g_targetH > 0 && (self.styleMask & NSWindowStyleMaskTitled) && !(self.styleMask & NSWindowStyleMaskDocModalWindow)) {
        if (g_lockMode == LOCK_MODE_STRICT) {
            frameRect.size.width = g_targetW;
            frameRect.size.height = g_targetH;
        } else if (g_lockMode == LOCK_MODE_CAP) {
            // Cap at target profile bounds
            if (frameRect.size.width > g_targetW) {
                frameRect.size.width = g_targetW;
            }
            if (frameRect.size.height > g_targetH) {
                // Adjust Y so top border stays in place if expanding upwards
                CGFloat deltaH = frameRect.size.height - g_targetH;
                frameRect.size.height = g_targetH;
                frameRect.origin.y += deltaH;
            }
        }
    }
    [self camou_setFrame:frameRect display:displayFlag animate:animateFlag];
}

@end

__attribute__((constructor))
static void InitCamouWindowLock(void) {
    const char *lock_env = getenv("CAMOU_LOCK_WINDOW_SIZE");
    if (!lock_env) return;
    int w = 0, h = 0;
    if (sscanf(lock_env, "%dx%d", &w, &h) != 2 || w <= 0 || h <= 0) return;

    // Only hook main browser process
    NSString *bundlePath = [[NSBundle mainBundle] bundlePath];
    if (![bundlePath hasSuffix:@"Chromium.app"] && ![bundlePath hasSuffix:@"CamouChromium-155.app"]) {
        return;
    }

    g_targetW = w;
    g_targetH = h;

    const char *mode_env = getenv("CAMOU_LOCK_MODE");
    if (mode_env && strcmp(mode_env, "STRICT_LOCK") == 0) {
        g_lockMode = LOCK_MODE_STRICT;
    } else {
        g_lockMode = LOCK_MODE_CAP;
    }

    NSLog(@"[CamouWindowLock] Activated mode=%d for %d x %d (bundle: %@)", g_lockMode, w, h, bundlePath);

    Class winClass = [NSWindow class];
    Swizzle(winClass, @selector(zoom:), @selector(camou_zoom:));
    Swizzle(winClass, @selector(toggleFullScreen:), @selector(camou_toggleFullScreen:));
    Swizzle(winClass, @selector(setStyleMask:), @selector(camou_setStyleMask:));
    Swizzle(winClass, @selector(setMinSize:), @selector(camou_setMinSize:));
    Swizzle(winClass, @selector(setMaxSize:), @selector(camou_setMaxSize:));
    Swizzle(winClass, @selector(setFrame:display:animate:), @selector(camou_setFrame:display:animate:));

    dispatch_async(dispatch_get_main_queue(), ^{
        [[NSNotificationCenter defaultCenter] addObserverForName:NSWindowDidUpdateNotification
                                                          object:nil
                                                           queue:[NSOperationQueue mainQueue]
                                                      usingBlock:^(NSNotification *note) {
            id obj = note.object;
            if (![obj isKindOfClass:[NSWindow class]]) return;
            NSWindow *win = (NSWindow *)obj;
            if (win.styleMask & NSWindowStyleMaskTitled) {
                // Keep maxSize strictly enforced
                if (g_targetW > 0 && g_targetH > 0) {
                    NSSize maxS = [win maxSize];
                    if (maxS.width > g_targetW || maxS.height > g_targetH) {
                        [win setMaxSize:NSMakeSize(g_targetW, g_targetH)];
                    }
                }
                if (g_lockMode == LOCK_MODE_STRICT) {
                    NSButton *zoomBtn = [win standardWindowButton:NSWindowZoomButton];
                    if (zoomBtn && [zoomBtn isEnabled]) {
                        [zoomBtn setEnabled:NO];
                    }
                    if (win.styleMask & NSWindowStyleMaskResizable) {
                        win.styleMask &= ~NSWindowStyleMaskResizable;
                    }
                } else if (g_lockMode == LOCK_MODE_CAP) {
                    // In desktop mode, if the window frame ever leaks beyond target bounds, clamp it immediately
                    NSRect curFrame = [win frame];
                    if (curFrame.size.width > g_targetW || curFrame.size.height > g_targetH) {
                        CGFloat clampedW = MIN(curFrame.size.width, (CGFloat)g_targetW);
                        CGFloat clampedH = MIN(curFrame.size.height, (CGFloat)g_targetH);
                        [win setFrame:NSMakeRect(curFrame.origin.x, curFrame.origin.y, clampedW, clampedH) display:YES animate:NO];
                    }
                }
            }
        }];
    });
}
