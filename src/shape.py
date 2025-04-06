import arcade

class Shape:
    def __init__(self, properties, color=(0, 0, 0, 255)):
        self.is_visible = True
        for prop in properties:
            setattr(self, prop, properties[prop])
        if isinstance(color, (list, tuple)) and len(color) == 4:
            self.color = tuple(int(max(0, min(255, c))) for c in color)
        elif isinstance(color, (list, tuple)) and len(color) == 3:
            self.color = (int(max(0, min(255, color[0]))),
                          int(max(0, min(255, color[1]))),
                          int(max(0, min(255, color[2]))),
                          255) # Add default alpha
        else:
             print(f"Warning: Invalid color value '{color}'. Using default black.")
             self.color = (0, 0, 0, 255)

    def draw(self,x,y):
        pass

class Rectangle(Shape):
    def __init__(self, width, height, color, **kwargs):
        super().__init__(kwargs, color)
        self.width = width
        self.height = height

    def draw(self,x,y):
        rect = arcade.rect.XYWH(
            width=self.width,
            height=self.height,
            x=x,
            y=y
        )
        arcade.draw_rect_filled(rect, self.color)

class Circle(Shape):
    def __init__(self, radius=10, color=(0, 0, 0, 255), **kwargs):
        super().__init__(kwargs, color)
        self.radius = radius

    def draw(self,x,y):
        arcade.draw_circle_filled(x, y, self.radius, self.color)

class Triangle(Shape):
    def __init__(self, p2=(10,0), p3=(5,10), color=(0, 0, 0, 255), **kwargs):
        super().__init__(kwargs, color)
        self.p2 = p2
        self.p3 = p3


    def draw(self, x, y):
        arcade.draw_triangle_filled(
            x, y,
            self.p2[0], self.p2[1],
            self.p3[0], self.p3[1],
            self.color
        )


class Line(Shape):
     def __init__(self, x2=10, y2=10, thickness=1, color=(0, 0, 0, 255), **kwargs):
         super().__init__(kwargs, color)
         self.x2 = x2
         self.y2 = y2
         self.thickness = thickness

     def draw(self, x, y):
         arcade.draw_line(x, y, self.x2, self.y2, self.color, self.thickness)