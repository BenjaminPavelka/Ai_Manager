from AppKit import (
    NSWindow, NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
    NSBackingStoreBuffered, NSMakeRect, NSApp, NSObject,
    NSWindowCollectionBehaviorFullScreenPrimary,
)
from WebKit import WKWebView, WKWebViewConfiguration
from Foundation import NSURL, NSURLRequest

from services_config import PORT

_window = None
_delegate = None
_webview = None


class _Delegate(NSObject):
    def windowWillClose_(self, _notification):
        global _window, _delegate, _webview
        _window = None
        _delegate = None
        _webview = None


def open_dashboard():
    global _window, _delegate, _webview

    if _window is not None:
        _window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)
        return

    style = (
        NSWindowStyleMaskTitled |
        NSWindowStyleMaskClosable |
        NSWindowStyleMaskMiniaturizable |
        NSWindowStyleMaskResizable
    )
    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(0, 0, 1100, 740), style, NSBackingStoreBuffered, False
    )
    win.setTitle_("AI Manager")
    win.setReleasedWhenClosed_(False)  # prevent crash when Python still holds a reference
    win.center()
    win.setCollectionBehavior_(NSWindowCollectionBehaviorFullScreenPrimary)

    delegate = _Delegate.alloc().init()
    win.setDelegate_(delegate)

    cfg = WKWebViewConfiguration.alloc().init()
    webview = WKWebView.alloc().initWithFrame_configuration_(
        win.contentView().bounds(), cfg
    )
    webview.setAutoresizingMask_(2 | 16)  # widthSizable | heightSizable
    win.contentView().addSubview_(webview)

    url = NSURL.URLWithString_(f"http://localhost:{PORT}")
    webview.loadRequest_(NSURLRequest.requestWithURL_(url))

    win.makeKeyAndOrderFront_(None)
    NSApp.activateIgnoringOtherApps_(True)

    _window = win
    _delegate = delegate
    _webview = webview
