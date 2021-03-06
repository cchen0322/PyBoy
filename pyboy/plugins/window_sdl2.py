#
# License: See LICENSE.md file
# GitHub: https://github.com/Baekalfen/PyBoy
#
import logging

import sdl2
import sdl2.ext
from pyboy.plugins.base_plugin import PyBoyWindowPlugin
from pyboy.utils import WindowEvent, WindowEventMouse

logger = logging.getLogger(__name__)

ROWS, COLS = 144, 160

try:
    from cython import compiled
    cythonmode = compiled
except ImportError:
    cythonmode = False

# https://wiki.libsdl.org/SDL_Scancode#Related_Enumerations
# yapf: disable
KEY_DOWN = {
    sdl2.SDLK_UP        : WindowEvent.PRESS_ARROW_UP,
    sdl2.SDLK_DOWN      : WindowEvent.PRESS_ARROW_DOWN,
    sdl2.SDLK_RIGHT     : WindowEvent.PRESS_ARROW_RIGHT,
    sdl2.SDLK_LEFT      : WindowEvent.PRESS_ARROW_LEFT,
    sdl2.SDLK_a         : WindowEvent.PRESS_BUTTON_A,
    sdl2.SDLK_s         : WindowEvent.PRESS_BUTTON_B,
    sdl2.SDLK_RETURN    : WindowEvent.PRESS_BUTTON_START,
    sdl2.SDLK_BACKSPACE : WindowEvent.PRESS_BUTTON_SELECT,
    sdl2.SDLK_SPACE     : WindowEvent.PRESS_SPEED_UP,
    sdl2.SDLK_COMMA     : WindowEvent.PRESS_REWIND_BACK,
    sdl2.SDLK_PERIOD    : WindowEvent.PRESS_REWIND_FORWARD,
}

KEY_UP = {
    sdl2.SDLK_UP        : WindowEvent.RELEASE_ARROW_UP,
    sdl2.SDLK_DOWN      : WindowEvent.RELEASE_ARROW_DOWN,
    sdl2.SDLK_RIGHT     : WindowEvent.RELEASE_ARROW_RIGHT,
    sdl2.SDLK_LEFT      : WindowEvent.RELEASE_ARROW_LEFT,
    sdl2.SDLK_a         : WindowEvent.RELEASE_BUTTON_A,
    sdl2.SDLK_s         : WindowEvent.RELEASE_BUTTON_B,
    sdl2.SDLK_RETURN    : WindowEvent.RELEASE_BUTTON_START,
    sdl2.SDLK_BACKSPACE : WindowEvent.RELEASE_BUTTON_SELECT,
    sdl2.SDLK_z         : WindowEvent.STATE_SAVE,
    sdl2.SDLK_x         : WindowEvent.STATE_LOAD,
    sdl2.SDLK_SPACE     : WindowEvent.RELEASE_SPEED_UP,
    sdl2.SDLK_p         : WindowEvent.PAUSE_TOGGLE,
    sdl2.SDLK_i         : WindowEvent.SCREEN_RECORDING_TOGGLE,
    sdl2.SDLK_ESCAPE    : WindowEvent.QUIT,
    sdl2.SDLK_COMMA     : WindowEvent.RELEASE_REWIND_BACK,
    sdl2.SDLK_PERIOD    : WindowEvent.RELEASE_REWIND_FORWARD,
}
# yapf: enable


def sdl2_event_pump(events):
    # Feed events into the loop
    for event in sdl2.ext.get_events():
        if event.type == sdl2.SDL_QUIT:
            events.append(WindowEvent(WindowEvent.QUIT))
        elif event.type == sdl2.SDL_KEYDOWN:
            events.append(WindowEvent(KEY_DOWN.get(event.key.keysym.sym, WindowEvent.PASS)))
        elif event.type == sdl2.SDL_KEYUP:
            events.append(WindowEvent(KEY_UP.get(event.key.keysym.sym, WindowEvent.PASS)))
        elif event.type == sdl2.SDL_WINDOWEVENT:
            if event.window.windowID == 1:
                if event.window.event == sdl2.SDL_WINDOWEVENT_FOCUS_LOST:
                    events.append(WindowEvent(WindowEvent.WINDOW_UNFOCUS))
                elif event.window.event == sdl2.SDL_WINDOWEVENT_FOCUS_GAINED:
                    events.append(WindowEvent(WindowEvent.WINDOW_FOCUS))
        elif event.type == sdl2.SDL_MOUSEMOTION or event.type == sdl2.SDL_MOUSEBUTTONUP:
            mouse_button = -1
            if event.type == sdl2.SDL_MOUSEBUTTONUP:
                if event.button.button == sdl2.SDL_BUTTON_LEFT:
                    mouse_button = 0
                elif event.button.button == sdl2.SDL_BUTTON_RIGHT:
                    mouse_button = 1

            events.append(
                WindowEventMouse(
                    WindowEvent._INTERNAL_MOUSE,
                    window_id=event.motion.windowID,
                    mouse_x=event.motion.x,
                    mouse_y=event.motion.y,
                    mouse_button=mouse_button
                )
            )
    return events


class WindowSDL2(PyBoyWindowPlugin):
    def __init__(self, pyboy, mb, pyboy_argv):
        super().__init__(pyboy, mb, pyboy_argv)

        if not self.enabled():
            return

        sdl2.SDL_Init(sdl2.SDL_INIT_EVERYTHING)
        self._ticks = sdl2.SDL_GetTicks()

        self._window = sdl2.SDL_CreateWindow(
            b"PyBoy", sdl2.SDL_WINDOWPOS_CENTERED, sdl2.SDL_WINDOWPOS_CENTERED, self._scaledresolution[0],
            self._scaledresolution[1], sdl2.SDL_WINDOW_RESIZABLE
        )

        self._sdlrenderer = sdl2.SDL_CreateRenderer(self._window, -1, sdl2.SDL_RENDERER_ACCELERATED)

        self._sdltexturebuffer = sdl2.SDL_CreateTexture(
            self._sdlrenderer, sdl2.SDL_PIXELFORMAT_RGBA8888, sdl2.SDL_TEXTUREACCESS_STATIC, COLS, ROWS
        )

        sdl2.SDL_ShowWindow(self._window)

    def set_title(self, title):
        sdl2.SDL_SetWindowTitle(self._window, title.encode())

    def handle_events(self, events):
        return sdl2_event_pump(events)

    def post_tick(self):
        self._update_display()

    def enabled(self):
        return self.pyboy_argv.get("window_type") == "SDL2" or self.pyboy_argv.get("window_type") is None

    def frame_limiter(self, speed):
        now = sdl2.SDL_GetTicks()
        delay = int(1000.0 / (60.0*speed) - (now - self._ticks))
        sdl2.SDL_Delay(delay if delay > 0 else 0)
        self._ticks = sdl2.SDL_GetTicks()
        return True

    def stop(self):
        sdl2.SDL_DestroyWindow(self._window)
        sdl2.SDL_Quit()


# Unfortunately CPython/PyPy code has to be hidden in an exec call to
# prevent Cython from trying to parse it. This block provides the
# functions that are otherwise implemented as inlined cdefs in the pxd
if not cythonmode:
    exec(
        """
def _update_display(self):
    sdl2.SDL_UpdateTexture(self._sdltexturebuffer, None, self.renderer._screenbuffer_ptr, COLS*4)
    sdl2.SDL_RenderCopy(self._sdlrenderer, self._sdltexturebuffer, None, None)
    sdl2.SDL_RenderPresent(self._sdlrenderer)
    sdl2.SDL_RenderClear(self._sdlrenderer)

WindowSDL2._update_display = _update_display
""", globals(), locals()
    )
