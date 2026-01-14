from machine import Pin, SPI
import framebuf

class LCD1Inch3(framebuf.FrameBuffer):
    """Driver class for 1.3 inch LCD display with 240x240 resolution.

    This class provides an interface to control a 1.3 inch LCD display
    using SPI communication. It extends framebuf.FrameBuffer to provide
    drawing capabilities with RGB565 color format.
    """
    def __init__(self):
        """Initialize the LCD display.

        Sets up the display with 240x240 resolution, configures SPI
        communication, initializes the frame buffer, and sets up
        pre-defined color constants.
        """
        self.BL = 13  # Pins used for display screen
        self.DC = 8
        self.RST = 12
        self.MOSI = 11
        self.SCK = 10
        self.CS = 9

        self.width = 240
        self.height = 240

        self.cs = Pin(self.CS,Pin.OUT)
        self.rst = Pin(self.RST,Pin.OUT)

        self.cs(1)
        self.spi = SPI(1)
        self.spi = SPI(1,1000_000)
        self.spi = SPI(1,100000_000,polarity=0, phase=0,sck=Pin(self.SCK),mosi=Pin(self.MOSI),miso=None)
        self.dc = Pin(self.DC,Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)
        self.init_display()

        self.red   =   0x07E0 # Pre-defined colours
        self.green =   0x001f # Probably easier to use colour(r,g,b) defined below
        self.blue  =   0xf800
        self.white =   0xffff

    def write_cmd(self, cmd):
        """Write a command byte to the display.

        Args:
            cmd: Command byte to send to the display.
        """
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        """Write a data byte to the display.

        Args:
            buf: Data byte to send to the display.
        """
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)

    def init_display(self):
        """Initialize the display with required configuration commands.

        Performs hardware reset and sends initialization sequence
        of commands to configure the display settings including
        orientation, color format, and display parameters.
        """
        self.rst(1)
        self.rst(0)
        self.rst(1)
        self.write_cmd(0x36)
        self.write_data(0x70)
        self.write_cmd(0x3A)
        self.write_data(0x05)
        self.write_cmd(0xB2)
        self.write_data(0x0C)
        self.write_data(0x0C)
        self.write_data(0x00)
        self.write_data(0x33)
        self.write_data(0x33)
        self.write_cmd(0xB7)
        self.write_data(0x35)
        self.write_cmd(0xBB)
        self.write_data(0x19)
        self.write_cmd(0xC0)
        self.write_data(0x2C)
        self.write_cmd(0xC2)
        self.write_data(0x01)
        self.write_cmd(0xC3)
        self.write_data(0x12)
        self.write_cmd(0xC4)
        self.write_data(0x20)
        self.write_cmd(0xC6)
        self.write_data(0x0F)
        self.write_cmd(0xD0)
        self.write_data(0xA4)
        self.write_data(0xA1)
        self.write_cmd(0xE0)
        self.write_data(0xD0)
        self.write_data(0x04)
        self.write_data(0x0D)
        self.write_data(0x11)
        self.write_data(0x13)
        self.write_data(0x2B)
        self.write_data(0x3F)
        self.write_data(0x54)
        self.write_data(0x4C)
        self.write_data(0x18)
        self.write_data(0x0D)
        self.write_data(0x0B)
        self.write_data(0x1F)
        self.write_data(0x23)
        self.write_cmd(0xE1)
        self.write_data(0xD0)
        self.write_data(0x04)
        self.write_data(0x0C)
        self.write_data(0x11)
        self.write_data(0x13)
        self.write_data(0x2C)
        self.write_data(0x3F)
        self.write_data(0x44)
        self.write_data(0x51)
        self.write_data(0x2F)
        self.write_data(0x1F)
        self.write_data(0x1F)
        self.write_data(0x20)
        self.write_data(0x23)
        self.write_cmd(0x21)
        self.write_cmd(0x11)
        self.write_cmd(0x29)

    def show(self):
        """Update the display with the current frame buffer contents.

        Sends the frame buffer data to the display via SPI,
        updating the visible screen with any drawing operations
        that have been performed.
        """
        self.write_cmd(0x2A)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0xef)
        self.write_cmd(0x2B)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0x00)
        self.write_data(0xEF)
        self.write_cmd(0x2C)
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(self.buffer)
        self.cs(1)

    # def taken from https://github.com/dhargopala/pico-custom-font/blob/main/lcd_lib.py
    def write_text(self,text,x,y,size,color):
        """Write text on OLED/LCD display with variable font size.

        Args:
            text: The string of characters to be displayed.
            x: X coordinate of starting position.
            y: Y coordinate of starting position.
            size: Font size multiplier for the text.
            color: Color of text to be displayed.
        """
        background = self.pixel(x,y)
        info = []

        # Creating reference charaters to read their values
        self.text(text,x,y,color)
        for i in range(x,x+(8*len(text))):
            for j in range(y,y+8):
                # Fetching amd saving details of pixels, such as
                # x co-ordinate, y co-ordinate, and color of the pixel
                px_color = self.pixel(i,j)
                if px_color == color:
                    info.append((i, j, px_color))

        # Clearing the reference characters from the screen
        self.text(text,x,y,background)

        # Writing the custom-sized font characters on screen
        for px_info in info:
            self.fill_rect(size*px_info[0] - (size-1)*x , size*px_info[1] - (size-1)*y, size, size, px_info[2])

# ========= End of Driver ===========
