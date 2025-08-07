import time
import os
import sys

from media.sensor import *
from media.display import *
from media.media import *
from machine import TOUCH

sensor = None

################################ 类 ############################################################
class Button:
    def __init__(self, x, y, radius, text, value_change, color=(128, 128, 128), min_value=0, max_value=255):
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.text = text
        self.value_change = value_change
        self.min_value = min_value
        self.max_value = max_value
        self.is_pressed = False
        self.last_press_time = 0
        self.long_press_threshold = 1000  # 长按阈值(毫秒)s
        self.long_press_interval = 100    # 长按后重复触发间隔(毫秒)
        self.last_long_press_time = 0

    def draw(self, img):
        """画一个-圆，一个text，一个+圆"""
        img.draw_circle(self.x, self.y, self.radius, color=self.color, fill=True)
        img.draw_string_advanced(self.x-10, self.y-18,30, f'{self.text}', color=(255,255,255))

    def is_touched(self, touch_x, touch_y):
        """直接坐标范围判断"""
        # 计算触摸点到按钮中心的距离平方
        dx = touch_x - self.x
        dy = touch_y - self.y
        distance_squared = dx * dx + dy * dy
        # 判断距离是否小于半径的平方（使用1.4倍半径作为缓冲）
        return distance_squared <= (self.radius * 1.4) ** 2

    def handle_touch(self, touch_x, touch_y, is_pressed, current_value,stride=0):
        """检测触摸事件并根据触摸状态更新按钮状态和返回值"""
        self.button_stride(stride)
        if is_pressed and self.is_touched(touch_x, touch_y):
#            print("sucessfully touch")
            current_time = time.ticks_ms()# 记录当前时间用于后续的长按检测
            # 短按处理(首次)
            if not self.is_pressed:
                self.is_pressed = False
                self.last_press_time = current_time
                self.last_long_press_time = current_time
                # max()保证不超最小，min()保证不超最大
                return max(self.min_value, min(self.max_value, current_value + self.value_change))
            # 长按检测
            press_duration = current_time - self.last_press_time
            if press_duration > self.long_press_threshold:
                # 快速增减
                if current_time - self.last_long_press_time > self.long_press_interval:
                    self.last_long_press_time = current_time
                    return max(self.min_value, min(self.max_value, current_value + self.value_change))
        else:
            self.is_pressed = False
        return current_value

    def button_model_change(self, touch_x, touch_y, is_pressed, current_model):
        """调试模式改变功能"""
        """
           model = 0 -> 灰度二值化阈值
           model = 1 -> RGB二值化阈值
        """
        current_model += 1
        if current_model == 2:
            current_model = 0
        return current_model

    def button_stride(self, stride_mode):
        """阈值步长模式功能"""
        """
           stride_mode = 0 -> 步长为1
           stride_mode = 1 -> 步长为10
        """
        sign = 1 if self.value_change > 0 else -1
        if stride_mode == 0:
            self.value_change = sign * 1
        if stride_mode == 1:
            self.value_change = sign * 10

################################ 函数 ############################################################
def draw_value(img,x,y,value,size=30):
    """文本显示"""
    img.draw_string_advanced(x, y-15, size, f'{value}', color=(255,255,255))

################################# 主函数 ############################################################
"""主函数的全局变量"""
min_binary = 0
max_binary = 255
min_L = 0
max_L = 255
min_A = 0
max_A = 255
min_B = 0
max_B = 255

model = 0   # 按键模式
state = 0   # 屏幕状态

state_press_up = False      # 按压加号按键状态
state_press_down = False    # 按压加号按键状态
state_press_model = False   # 按压model按键状态
state_pres = False          # 按压state状态
state_modulate = 0      # 按压调试状态
state_task = 1          # 按压任务状态
last_state = 0

stride_mode = 0

debounce_threshold = 200  # 防抖阈值(毫秒)

try:
# 创建按键实例
    #状态机按键
#状态0, 2, 3的界面按键
    bu_state = Button(30, 30, 20, text="S",value_change=1, min_value=0, max_value=4)
#状态1的界面按键
    bu_modulate = Button(250, 240, 60, text="A",value_change=0)
    bu_task = Button(580, 240, 60, text="B",value_change=0)
#状态2的界面按键
    # 调试模式改变按键
    bu_model = Button(120, 200, 20, text="m",value_change=0)
    # 阈值复位按键
    bu_reset = Button(120+280, 200, 20, text="r",value_change=0)
    # 步长改变按键
    bu_stride = Button(120+280+280, 200, 20, text="s",value_change=0)
    # 灰度min与max || L的min与max
    button1_up = Button(220, 30, 20, text="+",value_change=1)
    button1_down = Button(20, 30, 20, text="-",value_change=-1)
    button2_up = Button(220, 110, 20, text="+",value_change=1)
    button2_down = Button(20, 110, 20, text="-",value_change=-1)
    # A的min与max
    button3_up = Button(220+280, 30, 20, text="+",value_change=1)
    button3_down = Button(20+280, 30, 20, text="-",value_change=-1)
    button4_up = Button(220+280, 110, 20, text="+",value_change=1)
    button4_down = Button(20+280, 110, 20, text="-",value_change=-1)
    # B的min与max
    button5_up = Button(220+280+280, 30, 20, text="+",value_change=1)
    button5_down = Button(20+280+280, 30, 20, text="-",value_change=-1)
    button6_up = Button(220+280+280, 110, 20, text="+",value_change=1)
    button6_down = Button(20+280+280, 110, 20, text="-",value_change=-1)

    tp = TOUCH(0)

    # 创建图像缓冲区
    sensor = Sensor()
    sensor.reset()
    sensor.set_framesize(width=800, height=480,chn=CAM_CHN_ID_0)
    sensor.set_pixformat(Sensor.RGB565,chn=CAM_CHN_ID_0)

    #调制时的按键区的img
    img1 = image.Image(800, 240, image.RGB565)
    img1.clear()  # 确保所有像素为0
    #选择调制与任务时的img
    img_state1 = image.Image(800, 480, image.RGB565)
    img_state1.clear()

    Display.init(Display.ST7701,to_ide = True, osd_num = 2)
    MediaManager.init()
    sensor.run()
    clock = time.clock()
    last_touch_time = 0
    #死循环开始
    while True:
        clock.tick()
        os.exitpoint()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        #状态判断
        if state == 0:
            bu_state.draw(img)
            draw_value(img, 20, 60,f"state:{state},初始界面")

            img.draw_string_advanced(10, 200, 30, "f:{}".format(clock.fps()), color=(255, 0, 0))
            Display.show_image(img,x=0, y=0)
            Display.show_image(img,x=0, y=0, layer=Display.LAYER_OSD1)
            Display.show_image(img,x=0, y=0, layer=Display.LAYER_OSD2)
            img.compressed_for_ide()
        if state == 1:
            bu_modulate.draw(img_state1)
            draw_value(img_state1, 220, 140,"调试")
            bu_task.draw(img_state1)
            draw_value(img_state1, 550, 140,"任务")
            draw_value(img_state1, 20, 60,f"state:{state},选择界面")

            Display.show_image(img_state1,x=0, y=0)
            Display.show_image(img_state1,x=0, y=0, layer=Display.LAYER_OSD1)
            Display.show_image(img_state1,x=0, y=0, layer=Display.LAYER_OSD2)
            img_state1.compressed_for_ide()
        if state == 2:
            resized_img = img.midpoint_pool(2, 2)
            img1.clear()
            img2 = resized_img.copy()
            bu_model.draw(img1)
            bu_stride.draw(img1)
            if stride_mode == 0:
                draw_value(img1, 60+280+280, 160, "步长：1")
            if stride_mode == 1:
                draw_value(img1, 60+280+280, 160, "步长：10")
            bu_reset.draw(img1)
            draw_value(img1, 60+280, 160, "复位")

            bu_state.draw(resized_img)
            draw_value(resized_img, 20, 60,f"state:{state},调试界面")
            #显示当前的模式-灰度模式||RGB模式
            if model == 0:
               img2 = img2.to_grayscale()
               draw_value(img1, 60, 160, "GRAY模式")
               #第1列
               button1_down.draw(img1)
               button1_up.draw(img1)
               draw_value(img1, 120, 30, min_binary)
               button2_down.draw(img1)
               button2_up.draw(img1)
               draw_value(img1, 120, 110, max_binary)

               img2.binary([(min_binary,max_binary)])
            else:
               img2 = img2.to_rgb565()
               draw_value(img1, 60, 160, "RGB模式")
               #第1列
               button1_down.draw(img1)
               button1_up.draw(img1)
               draw_value(img1, 120, 30, min_L)
               button2_down.draw(img1)
               button2_up.draw(img1)
               draw_value(img1, 120, 110, max_L)
               #第2列
               button3_down.draw(img1)
               button3_up.draw(img1)
               draw_value(img1, 120+280, 30, min_A)
               button4_down.draw(img1)
               button4_up.draw(img1)
               draw_value(img1, 120+280, 110, max_A)
               #第3列
               button5_down.draw(img1)
               button5_up.draw(img1)
               draw_value(img1, 120+280+280, 30, min_B)
               button6_down.draw(img1)
               button6_up.draw(img1)
               draw_value(img1, 120+280+280, 110, max_B)

               img2.binary([(min_L, max_L,
                            min_A, max_A,
                            min_B, max_B)])

            img2.draw_string_advanced(10, 200, 30, "f:{}".format(clock.fps()), color=(255, 0, 0))
            Display.show_image(resized_img,x=0, y=0)
            Display.show_image(img1,x=0, y=240,layer=Display.LAYER_OSD1)
            Display.show_image(img2,x=400, y=0,layer=Display.LAYER_OSD2)
            img2.compressed_for_ide()
        if state == 3:
            bu_state.draw(img)
            draw_value(img, 20, 60,f"state:{state},任务界面")

            img.draw_string_advanced(10, 200, 30, "f:{}".format(clock.fps()), color=(255, 0, 0))
            Display.show_image(img,x=0, y=0)
            Display.show_image(img,x=0, y=0,layer=Display.LAYER_OSD1)
            Display.show_image(img,x=0, y=0,layer=Display.LAYER_OSD2)
            img.compressed_for_ide()

        # 读取触摸
        ps = tp.read(1)
        if ps:
           x = ps[0].x
           y = ps[0].y
           event = ps[0].event
           current_time = time.ticks_ms()
           if current_time - last_touch_time < debounce_threshold:
                continue
           # 事件按键并进入handle_touch判断
           if  event == 3:
                last_touch_time = current_time
                if  event == 3:
################################# 初始模式 ##################################################################
                    if state == 0:
                        if 0.8*bu_state.x < x < 1.8*bu_state.x and 0.8*bu_state.y < y < 1.8*bu_model.y:
                            state = 1

################################# 选择模式 ##################################################################
                    if state == 1:
                        if 0.5*bu_modulate.x < x < 1.5*bu_modulate.x and 0.5*bu_modulate.y < y < 1.5*bu_modulate.y:
                            state = 2
                        if 0.5*bu_task.x < x < 1.5*bu_task.x and 0.5*bu_task.y < y < 1.5*bu_task.y:
                            state = 3

################################# 调试模式 ##################################################################
                    if state == 2:
                        if 0.8*bu_state.x < x < 1.2*bu_state.x and 0.8*bu_state.y < y < 1.2*bu_model.y:
                            state = 0
                            blank = image.Image(800, 480, image.RGB565)
                            blank.clear()
                            Display.show_image(blank,x=0, y=0, layer=Display.LAYER_OSD1)
                            Display.show_image(blank,x=0, y=0, layer=Display.LAYER_OSD2)

                        y = ps[0].y-240
                        # 复位
                        if 0.8*bu_reset.x < x < 1.2*bu_reset.x and 0.8*bu_reset.y < y < 1.2*bu_reset.y:
                            min_binary = 0
                            max_binary = 255
                            min_L = 0
                            max_L = 255
                            min_A = 0
                            max_A = 255
                            min_B = 0
                            max_B = 255
                        # 步长
                        if 0.8*bu_stride.x < x < 1.2*bu_stride.x and 0.8*bu_stride.y < y < 1.2*bu_stride.y:
                            stride_mode = not stride_mode
                        # 模式
                        if 0.8*bu_model.x < x < 1.2*bu_model.x and 0.8*bu_model.y < y < 1.2*bu_model.y:
                           state_press_model = True
                           model = bu_model.button_model_change(x, y, state_press_up, model)
                           state_press_model = False
                        # 灰度图阈值
                        if model == 0:
                            new1_value = min_binary
                            new2_value = max_binary
                            # 判断为右边加号按键
                            if x-100 > 0:
                                state_press_up = True
                                if y < 90:# 判断为y更高的按键
                                    new1_value = button1_up.handle_touch(x, y, state_press_up, new1_value,stride=stride_mode)
                                    min_binary = new1_value
                                else:
                                    new2_value = button2_up.handle_touch(x, y, state_press_up, new2_value,stride=stride_mode)
                                    max_binary = new2_value
                                state_press_up = False
                            # 判断为左边减号按键
                            if x-100 < 0:
                                state_press_down = True
                                if y < 90:# 判断为y更高的按键
                                    new1_value = button1_down.handle_touch(x, y, state_press_down, new1_value,stride=stride_mode)
                                    min_binary = new1_value
                                else:
                                    new2_value = button2_down.handle_touch(x, y, state_press_down, new2_value,stride=stride_mode)
                                    max_binary = new2_value
                                state_press_down = False

                            min_binary = new1_value
                            max_binary = new2_value
                            draw_value(img1, 120, 30, min_binary)
                            draw_value(img1, 120, 110, max_binary)

                        # RGB图阈值
                        if model == 1:
                            new1L_value = min_L
                            new2L_value = max_L
                            new1A_value = min_A
                            new2A_value = max_A
                            new1B_value = min_B
                            new2B_value = max_B
                            # 判断为第一列右边加号按键
                            if x-100 > 0:
                                state_press_up = True
                                if y < 90:# 判断为y更高的按键
                                    new1L_value = button1_up.handle_touch(x, y, state_press_up, new1L_value,stride=stride_mode)
                                    min_L = new1L_value
                                else:
                                    new2L_value = button2_up.handle_touch(x, y, state_press_up, new2L_value,stride=stride_mode)
                                    max_L = new2L_value
                                state_press_up = False
                            if x-100 < 0:# 判断为左边减号按键
                                state_press_down = True
                                if y < 90:# 判断为y更高的按键
                                    new1L_value = button1_down.handle_touch(x, y, state_press_down, new1L_value,stride=stride_mode)
                                    min_L = new1L_value
                                else:
                                    new2L_value = button2_down.handle_touch(x, y, state_press_down, new2L_value,stride=stride_mode)
                                    max_L = new2L_value
                                state_press_down = False

                            # 判断为第二列右边加号按键
                            if x-(100+280) > 0:
                                state_press_up = True
                                if y < 90:# 判断为y更高的按键
                                    new1A_value = button3_up.handle_touch(x, y, state_press_up, new1A_value,stride=stride_mode)
                                    min_A = new1A_value
                                else:
                                    new2A_value = button4_up.handle_touch(x, y, state_press_up, new2A_value,stride=stride_mode)
                                    max_A = new2A_value
                                state_press_up = False
                            if x-(100+280) < 0:# 判断为左边减号按键
                                state_press_down = True
                                if y < 90:# 判断为y更高的按键
                                    new1A_value = button3_down.handle_touch(x, y, state_press_down, new1A_value,stride=stride_mode)
                                    min_A = new1A_value
                                else:
                                    new2A_value = button4_down.handle_touch(x, y, state_press_down, new2A_value,stride=stride_mode)
                                    max_A = new2A_value
                                state_press_down = False

                            # 判断为第3列右边加号按键
                            if x-(100+280+280) > 0:
                                state_press_up = True
                                if y < 90:# 判断为y更高的按键
                                    new1B_value = button5_up.handle_touch(x, y, state_press_up, new1B_value,stride=stride_mode)
                                    min_B = new1B_value
                                else:
                                    new2B_value = button6_up.handle_touch(x, y, state_press_up, new2B_value,stride=stride_mode)
                                    max_B = new2B_value
                                state_press_up = False
                            if x-(100+280+280) < 0: # 判断为左边减号按键
                                state_press_down = True
                                if y < 90:# 判断为y更高的按键
                                    new1B_value = button5_down.handle_touch(x, y, state_press_down, new1B_value,stride=stride_mode)
                                    min_B = new1B_value
                                else:
                                    new2B_value = button6_down.handle_touch(x, y, state_press_down, new2B_value,stride=stride_mode)
                                    max_B = new2B_value
                                state_press_down = False

                            min_L = new1L_value
                            max_L = new2L_value
                            min_A = new1A_value
                            max_A = new2A_value
                            min_B = new1B_value
                            max_B = new2B_value
                            draw_value(img1, 120, 30, new1L_value)
                            draw_value(img1, 120, 110, new2L_value)
                            draw_value(img1, 120+280, 30, new1A_value)
                            draw_value(img1, 120+280, 110, new2A_value)
                            draw_value(img1, 120+280+280, 30, new1B_value)
                            draw_value(img1, 120+280+280, 110, new2B_value)

################################# 任务模式 ##################################################################
                    if state == 3:
                        if 0.5*bu_state.x < x < 1.5*bu_state.x and 0.5*bu_state.y < y < 1.5*bu_model.y:
                            state = 0
                        """任务代码开始"""



                        """任务代码结束"""

except KeyboardInterrupt as e:
    print("user stop: ", e)
except BaseException as e:
    print(f"Exception {e}")
except DeprecationWarning as e:
    print(f"DeprecationWarning{e}")
finally:
    if isinstance(sensor, Sensor):
        sensor.stop()
    # deinit display
    Display.deinit()

    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(200)
    # release media buffer
    MediaManager.deinit()

