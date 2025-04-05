import threading
import queue

from interpreter import Vec2
from shape import *

class GameView(arcade.View):
    def __init__(self, controller, command_queue):
        super().__init__()
        self.controller = controller
        self.background_color = (255, 255, 255)
        self.shapes: list[(float, float, Shape)] = []
        self.command_queue = command_queue

    def process_commands(self):
        try:
            command = self.command_queue.get_nowait()
            cmd_type = command[0]
            args = command[1:]

            if cmd_type == "set_background":
                color, = args
                self.background_color = color
            elif cmd_type == "set_window_size":
                # FIXME: This is broken for now
                w, h = args
                self.controller.set_window_size(w, h)
            elif cmd_type == "bg_color":
                color, = args
                self.background_color = color
            elif cmd_type == "draw":
                point, shape, = args
                self.shapes.append((point, shape))

            self.command_queue.task_done()
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Error processing graphics commands: {e}")

    def on_update(self, delta_time):
        self.process_commands()

        if self.controller and self.controller.interpreter_visitor:
            try:
                self.controller.interpreter_visitor.execute_event('update', [delta_time])
            except Exception as e:
                print(f"Error scheduling update handler: {e}")

    def on_mouse_release(self, x: int, y: int, button: int, modifiers: int) -> bool | None:
        if self.controller and self.controller.interpreter_visitor:
            try:
                self.controller.interpreter_visitor.execute_event('click', [Vec2(x, y), button, modifiers])
            except Exception as e:
                print(f"Error scheduling click handler: {e}")

    def on_draw(self):
        self.clear(self.background_color)

        for point, shape in self.shapes:
            if shape.is_visible:
                shape.draw(point.x, point.y)

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            print("ESC pressed, closing the window...")
            self.controller.kill_display()

class GraphicsController:
    def __init__(self, window_size=(800, 600)):
        self.window = None
        self.game_view = None
        self.window_size = window_size
        self._arcade_thread = None
        self.command_queue = queue.Queue()
        self._stop_event = threading.Event()

        self.interpreter_visitor = None

    def add_visitor(self, visitor):
        self.interpreter_visitor = visitor

    def start_display(self):
        if self.window is None:
            self._arcade_thread = threading.Thread(target=self._run_arcade, daemon=True)
            self._arcade_thread.start()

    def _run_arcade(self):
        try:
            width, height = self.window_size
            self.window = arcade.Window(width, height, "MIASI-lang interpreter", resizable=True)
            self.game_view = GameView(self, self.command_queue)
            self.window.show_view(self.game_view)
            arcade.run()
        except Exception as e:
            print(f"Error in Arcade thread: {e}")
        finally:
            self.window = None
            self.game_view = None
            self._stop_event.set()

    def draw_shape(self, point, shape: Shape):
        self.command_queue.put(("draw", point, shape))

    def wait_for_display_close(self):
        if self._arcade_thread:
            self._stop_event.wait()
            self._arcade_thread.join(timeout=1.0)

    def kill_display(self):
        if self.window is not None:
            self.window.close()
            self.window = None

    def set_window_width(self, width):
        self.command_queue.put(("set_window_size", width, self.window_size[1]))

    def set_window_height(self, height):
        self.command_queue.put(("set_window_size", self.window_size[0], height))

    def set_background_color(self, color):
        self.command_queue.put(("bg_color", color))