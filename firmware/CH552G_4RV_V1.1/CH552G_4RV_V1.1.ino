#include <WS2812.h>

// ===== 硬件配置相关宏定义 =====
#define NUM_SLIDERS 4          // 滑块总数
#define NUM_LEDS 6             // LED灯珠总数
#define COLOR_PER_LEDS 3       // 每个LED的颜色通道数（RGB）
#define NUM_BYTES (NUM_LEDS*COLOR_PER_LEDS)  // LED数据总字节数

// ===== 阈值和时间相关宏定义 =====
#define ANALOG_THRESHOLD_LOW  5     // 模拟输入最低阈值
#define ANALOG_THRESHOLD_HIGH 250   // 模拟输入最高阈值
#define MAX_BRIGHTNESS 255          // LED最大亮度
#define FLOWING_BRIGHTNESS 64       // 流动效果亮度
#define PROGRESS_BRIGHTNESS 128     // 进度条效果亮度
#define BREATHING_BRIGHTNESS 192    // 呼吸灯效果亮度
#define INACTIVE_TIMEOUT 2000       // 无活动超时时间（毫秒）
#define MIN_FRAME_INTERVAL 5        // 旋钮变化时最快每5ms发送一次
#define HEARTBEAT_INTERVAL 100      // 静止时每100ms发送一次状态帧

// ===== 枚举定义 =====
enum TaskState {               // 任务状态枚举
  TASK1,                      // 任务1：读取输入并发送数据
  TASK2,                      // 任务2：LED效果更新
  TASK3,                      // 任务3：按键处理
  NUM_TASKS                   // 任务总数
};

enum LedMode {                // LED显示模式枚举
  MODE_PROGRESS,             // 旋钮音量进度条
  MODE_BREATHING,            // 呼吸灯
  MODE_SYNC_COLOR,           // 所有灯珠同步变色
  MODE_RAINBOW               // 幻彩灯
};

// ===== 硬件引脚定义 =====
const int buttonPin = 16;                          // 按钮输入引脚
const int analogInputs[NUM_SLIDERS] = {11, 15, 14, 32};  // 模拟输入引脚数组

// ===== 时间常量 =====
const unsigned long TICK_INTERVAL = 1;             // 任务调度时间间隔（毫秒）
const unsigned long DEBOUNCE_DELAY = 20;          // 按键消抖延时（毫秒）
const unsigned long taskIntervals[NUM_TASKS] = {   // 各任务执行间隔（毫秒）
  2,    // TASK1 每2ms读取旋钮
  5,    // TASK2 每5ms更新LED
  1     // TASK3 每1ms执行
};

// ===== 颜色配置 =====
const uint8_t SLIDER_COLORS[NUM_SLIDERS][3] = {    // 滑块对应LED颜色配置
  {0, 255, 0},   // 绿色
  {0, 0, 255},   // 蓝色
  {255, 0, 0},   // 红色
  {255, 255, 0}  // 黄色
};

// ===== 全局变量 =====
__xdata uint8_t ledData[NUM_BYTES];               // LED显示数据缓冲区
unsigned long lastTick = 0;                       // 上次主循环执行时间
int analogSliderValues[NUM_SLIDERS];              // 当前滑块值数组
int lastSliderValues[NUM_SLIDERS] = {0};         // 上次滑块值数组
bool isActive[NUM_SLIDERS] = {false};            // 滑块活动状态标志
int currentMode = MODE_BREATHING;                 // 当前LED显示模式
int selectedEffect = MODE_BREATHING;              // 按钮选中的待机灯效
unsigned long lastActivityTime = 0;               // 最后活动时间
int lastActiveSlider = -1;                       // 最后活动的滑块索引
unsigned long taskLastRun[NUM_TASKS] = {0};      // 各任务上次执行时间
unsigned long lastFrameTime = 0;                 // 上次发送旋钮帧的时间
bool sliderValuesChanged = true;                 // 是否有待发送的旋钮变化

// ===== 函数声明 =====
// LED相关函数
void setIndividualLEDColor(uint8_t ledIndex, uint8_t red, uint8_t green, 
    uint8_t blue, uint8_t brightness);  // 设置单个LED的颜色和亮度
void updateLEDProgressBar();    // 更新LED进度条显示效果
void flowingColorEffect();      // 实现流动彩虹灯效果
void breathingEffect();         // 实现呼吸灯效果
void synchronizedColorEffect(); // 所有灯珠同步变色

// 按键处理函数
void handleButtonEvents();      // 处理按键输入与消抖
void cycleLedEffect();          // 切换呼吸、同步变色、幻彩灯效

// 输入处理函数
void readAnalogInputs();        // 读取并处理所有滑块的输入值
void sendSliderValues();        // 将滑块值通过串口发送
int mapValue(int inputValue);   // 将输入值映射到目标范围

// 任务相关函数
void task1();                   // 执行滑块输入读取和数据发送
void task2();                   // 执行LED显示效果更新
void task3();                   // 执行按键输入处理
void scheduleTasks();           // 按预设间隔调度执行各任务

// 初始化函数：设置引脚模式
void setup() {
  // === 配置LED控制引脚 ===
  pinMode(17, OUTPUT);        // 设置P1.7引脚为输出模式，用于控制WS2812 LED
  
  // === 配置按键输入引脚 ===
  pinMode(buttonPin, INPUT_PULLUP);  // 设置按键引脚为上拉输入模式，默认高电平

  // === 配置模拟输入引脚 ===
  for (int i = 0; i < NUM_SLIDERS; i++) {
    pinMode(analogInputs[i], INPUT);  // 设置所有滑块引脚为输入模式
  }
}

// 主循环函数：按固定时间间隔执行任务调度
void loop() {
  // === 获取当前系统时间 ===
  unsigned long currentMillis = millis();
  
  // === 检查是否达到任务执行间隔 ===
  // 每隔TICK_INTERVAL毫秒执行一次任务调度
  if (currentMillis - lastTick >= TICK_INTERVAL) {
    lastTick = currentMillis;        // 更新上次执行时间
    scheduleTasks();                 // 执行任务调度
  }
}

// 任务1：执行滑块输入读取和数据发送的主要任务函数
// 按照预设的时间间隔定期执行，确保及时响应滑块变化
void task1() {
  readAnalogInputs();    // 读取并处理所有滑块的输入值
  unsigned long currentMillis = millis();
  unsigned long elapsed = currentMillis - lastFrameTime;
  // 旋钮运动时低延迟发送；静止时只保留心跳，避免USB阻塞按键扫描。
  if ((sliderValuesChanged && elapsed >= MIN_FRAME_INTERVAL) ||
      elapsed >= HEARTBEAT_INTERVAL) {
    sendSliderValues();
    sliderValuesChanged = false;
    lastFrameTime = currentMillis;
  }
}

// 读取并处理所有滑块的模拟输入值
// 功能：
// 1. 读取模拟输入值并应用阈值限制
// 2. 检测滑块活动状态并更新显示模式
// 3. 将处理后的值存储到全局数组中
void readAnalogInputs() {
  // === 遍历所有滑块 ===
  for (int i = 0; i < NUM_SLIDERS; i++) {
    // 读取当前滑块的模拟值
    int currentValue = analogRead(analogInputs[i]);
    
    // === 应用阈值限制，消除噪声 ===
    if (currentValue < ANALOG_THRESHOLD_LOW) {
        currentValue = 0;         // 低于最小阈值视为0
    } else if (currentValue > ANALOG_THRESHOLD_HIGH) {
        currentValue = 255;       // 高于最大阈值视为最大值
    }
    
    // === 检测滑块活动状态 ===
    // ADC每变化一级就立即响应，快速旋转时不会漏掉中间位置。
    if (currentValue != lastSliderValues[i]) {
      isActive[i] = true;
      lastSliderValues[i] = currentValue;
      
      // === 更新显示模式和相关状态 ===
      currentMode = MODE_PROGRESS;     // 切换到进度条显示模式
      lastActivityTime = millis();     // 记录活动时间
      lastActiveSlider = i;           // 记录当前活动的滑块
    }
    
    // 将处理后的值映射到目标范围并存储
    int mappedValue = mapValue(currentValue);
    if (mappedValue != analogSliderValues[i]) {
      analogSliderValues[i] = mappedValue;
      sliderValuesChanged = true;
    }
  }
}

// 将输入值从0-255范围映射到0-1023范围
// 参数：
// - inputValue: 输入值（0-255）
// 返回：
// - 映射后的值（0-1023）
int mapValue(int inputValue) {
  // 1023 = 4*255+3；纯整数映射比CH552上的浮点计算快得多。
  return inputValue * 4 + inputValue / 85;
}

// 将滑块值格式化并通过串口发送
// 格式：value1|value2|value3|value4
// 旋钮数据始终保持真实 ADC 方向：逆时针增大。
void sendSliderValues() {
  // === 初始化字符串缓冲区 ===
  static char builtString[20];    // 静态分配缓冲区，避免重复创建
  int currentLength = 0;          // 当前字符串长度
  
  // === 构建数据字符串 ===
  for (int i = 0; i < NUM_SLIDERS; i++) {
    // 添加分隔符（除第一个值外）
    if (i) builtString[currentLength++] = '|';
    
    // 将数值转换为字符串并添加到缓冲区
    currentLength += sprintf(builtString + currentLength, "%d", analogSliderValues[i]);
  }
  
  // === 完成字符串构建并发送 ===
  builtString[currentLength] = '\0';  // 添加字符串结束符
  USBSerial_println(builtString);     // 通过串口发送数据
}

// 任务2：根据当前模式和状态更新LED显示效果
void task2() {
  // === 获取当前时间用于超时检测 ===
  unsigned long currentMillis = millis();
  
  // === 自动模式切换逻辑 ===
  // 旋钮停止操作后，恢复按钮选中的待机灯效
  if (currentMode == MODE_PROGRESS && 
      (currentMillis - lastActivityTime) >= INACTIVE_TIMEOUT) {
    currentMode = selectedEffect;
    lastActiveSlider = -1;            // 清除最后活动滑块记录
  }

  switch (currentMode) {
    case MODE_PROGRESS:
      updateLEDProgressBar();
      break;
    case MODE_BREATHING:
      breathingEffect();
      break;
    case MODE_SYNC_COLOR:
      synchronizedColorEffect();
      break;
    case MODE_RAINBOW:
      flowingColorEffect();
      break;
  }
}

// 设置单个LED的RGB颜色和亮度
// 参数说明：
// - ledIndex: LED灯珠的索引号（0 ~ NUM_LEDS-1）
// - red: 红色分量值（0-255）
// - green: 绿色分量值（0-255）
// - blue: 蓝色分量值（0-255）
// - brightness: 整体亮度值（0-255）
void setIndividualLEDColor(uint8_t ledIndex, uint8_t red, uint8_t green, uint8_t blue, uint8_t brightness) {
  // === 计算带亮度的RGB值 ===
  // 使用8位右移运算代替除法，提高效率
  // 将每个颜色分量与亮度值相乘并缩放到0-255范围
  uint8_t red_bright = (red * brightness) >> 8;     // 计算最终红色亮度
  uint8_t green_bright = (green * brightness) >> 8; // 计算最终绿色亮度
  uint8_t blue_bright = (blue * brightness) >> 8;   // 计算最终蓝色亮度

  // 将计算后的RGB值写入LED数据缓冲区
  set_pixel_for_GRB_LED(ledData, ledIndex, red_bright, green_bright, blue_bright);
}

// 更新LED进度条显示效果：根据滑块值显示对应颜色和亮度的进度条
void updateLEDProgressBar() {
  // === 获取当前活动滑块的颜色信息 ===
  uint8_t colorR = SLIDER_COLORS[lastActiveSlider][0];  // 获取对应滑块的红色分量
  uint8_t colorG = SLIDER_COLORS[lastActiveSlider][1];  // 获取对应滑块的绿色分量
  uint8_t colorB = SLIDER_COLORS[lastActiveSlider][2];  // 获取对应滑块的蓝色分量
  
  // === 计算进度条显示参数 ===
  const int totalLEDs = NUM_LEDS;                       // LED总数
  const int stepsPerLED = 1024 / totalLEDs;            // 每个LED对应的值范围
  // 最终标准：逆时针旋转为音量增大，数值与灯条都直接使用 ADC 正方向。
  int sliderValue = analogSliderValues[lastActiveSlider];
  int fullLEDs = sliderValue / stepsPerLED;            // 计算完全点亮的LED数量
  // 计算最后一个LED的亮度百分比
  uint8_t partialLEDBrightness =
      (uint16_t)(sliderValue % stepsPerLED) * PROGRESS_BRIGHTNESS / stepsPerLED;

  // === 设置每个LED的显示状态 ===
  for (int i = 0; i < totalLEDs; i++) {
    int ledIndex = i;  // 从左向右显示进度
    
    if (i < fullLEDs) {
      // 完全点亮的LED
      setIndividualLEDColor(ledIndex, colorR, colorG, colorB, PROGRESS_BRIGHTNESS);
    } else if (i == fullLEDs) {
      // 部分点亮的LED（渐变效果）
      setIndividualLEDColor(ledIndex, colorR, colorG, colorB, 
                           partialLEDBrightness);
    } else {
      // 未点亮的LED
      setIndividualLEDColor(ledIndex, 0, 0, 0, 0);
    }
  }
  
  // 更新LED显示
  neopixel_show_P1_7(ledData, NUM_BYTES);
}

// 实现流动彩虹效果：通过HSV色彩空间实现平滑的颜色过渡
void flowingColorEffect() {
  static uint8_t hueStart = 0;    // 静态变量，保存起始色相值（0-255）

  // 为每个LED设置颜色
  for (int i = 0; i < NUM_LEDS; i++) {
    // 计算当前LED的色相值：起始色相 + 位置偏移
    // 使用取模运算确保色相值在0-255范围内循环
    uint8_t hue = (hueStart + i * (255 / NUM_LEDS)) % 255;

    // 声明RGB分量变量
    uint8_t red = 0, green = 0, blue = 0;
    
    // HSV转RGB的简化算法
    // 将0-255的色相范围分为三个区间，每个区间实现两个颜色之间的渐变
    if (hue < 85) {  // 红色渐变为绿色
      red = 255 - hue * 3;    // 红色递减
      green = hue * 3;        // 绿色递增
      blue = 0;              // 蓝色保持为0
    } else if (hue < 170) {  // 绿色渐变为蓝色
      hue -= 85;            // 调整色相值到0-85范围
      red = 0;              // 红色保持为0
      green = 255 - hue * 3; // 绿色递减
      blue = hue * 3;        // 蓝色递增
    } else {  // 蓝色渐变为红色
      hue -= 170;           // 调整色相值到0-85范围
      red = hue * 3;        // 红色递增
      green = 0;            // 绿色保持为0
      blue = 255 - hue * 3; // 蓝色递减
    }

    // 设置LED颜色，使用预定义的流动效果亮度
    setIndividualLEDColor(i, red, green, blue, FLOWING_BRIGHTNESS);
  }

  // 将数据更新到LED硬件
  neopixel_show_P1_7(ledData, NUM_BYTES);

  // 递增起始色相值，实现颜色流动
  // 使用取模运算确保在0-255范围内循环
  hueStart = (hueStart + 1) % 255;
}

// 实现呼吸灯效果：使LED亮度周期性变化
void breathingEffect() {
  // === 初始化呼吸效果参数 ===
  static uint8_t breathIndex = 0;     // 呼吸效果索引（0-255）
  static bool increasing = true;       // 亮度是否在增加
  // === 更新呼吸索引 ===
  if (increasing) {
    // 亮度递增
    if (++breathIndex >= 255) increasing = false;
  } else {
    // 亮度递减
    if (--breathIndex <= 0) increasing = true;
  }
  
  // === 计算当前亮度 ===
  uint8_t brightness = ((uint16_t)breathIndex * BREATHING_BRIGHTNESS) >> 8;

  // === 设置所有LED的颜色和亮度 ===
  for (int i = 0; i < NUM_LEDS; i++) {
    setIndividualLEDColor(i, 0, 255, 120, brightness);
  }
  
  // 更新LED显示
  neopixel_show_P1_7(ledData, NUM_BYTES);
}

// 同步变色：所有灯珠保持同一颜色，并一起平滑循环色相。
void synchronizedColorEffect() {
  static uint8_t hue = 0;
  uint8_t red = 0, green = 0, blue = 0;
  uint8_t phase = hue;
  if (phase < 85) {
    red = 255 - phase * 3;
    green = phase * 3;
  } else if (phase < 170) {
    phase -= 85;
    green = 255 - phase * 3;
    blue = phase * 3;
  } else {
    phase -= 170;
    red = phase * 3;
    blue = 255 - phase * 3;
  }
  for (int i = 0; i < NUM_LEDS; i++) {
    setIndividualLEDColor(i, red, green, blue, FLOWING_BRIGHTNESS);
  }
  neopixel_show_P1_7(ledData, NUM_BYTES);
  hue++;
}

// 每次按键依次切换：呼吸灯 -> 同步变色 -> 幻彩灯 -> 呼吸灯
void cycleLedEffect() {
  if (selectedEffect == MODE_BREATHING) {
    selectedEffect = MODE_SYNC_COLOR;
    USBSerial_println("FX|SYNC");
  } else if (selectedEffect == MODE_SYNC_COLOR) {
    selectedEffect = MODE_RAINBOW;
    USBSerial_println("FX|RAINBOW");
  } else {
    selectedEffect = MODE_BREATHING;
    USBSerial_println("FX|BREATHING");
  }
  currentMode = selectedEffect;
  lastActiveSlider = -1;
}

// 任务3：处理按键输入
void task3() {
  handleButtonEvents();
}

// 处理按键事件：按下按钮就切换，避免短按在释放阶段漏触发。
void handleButtonEvents() {
  static unsigned long lastDebounceTime = 0;
  static int lastButtonState = HIGH;
  static int debouncedButtonState = HIGH;
  unsigned long currentMillis = millis();
  int currentButtonState = digitalRead(buttonPin);

  if (currentButtonState != lastButtonState) {
    lastDebounceTime = currentMillis;
    lastButtonState = currentButtonState;
  }

  if ((currentMillis - lastDebounceTime) >= DEBOUNCE_DELAY &&
      currentButtonState != debouncedButtonState) {
    debouncedButtonState = currentButtonState;
    if (debouncedButtonState == LOW) cycleLedEffect();
  }
}

// 任务调度器：按照预设间隔执行各个任务
void scheduleTasks() {
  // 获取当前系统时间
  unsigned long currentMillis = millis();
  
  // 遍历所有任务
  for (int i = 0; i < NUM_TASKS; i++) {
    // 检查每个任务是否到达执行时间间隔
    if (currentMillis - taskLastRun[i] >= taskIntervals[i]) {
      // 更新任务的最后执行时间
      taskLastRun[i] = currentMillis;
      
      // 根据任务索引执行对应任务
      switch (i) {
        case TASK1:  // 执行任务1：读取滑块输入并发送数据
          task1();
          break;
        case TASK2:  // 执行任务2：LED效果更新
          task2();
          break;
        case TASK3:  // 执行任务3：按键处理
          task3();
          break;
      }
    }
  }
}
