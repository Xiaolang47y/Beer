# Beer
Beer (**B**e **E**mulator mor**E** **R**uined) 是一个基于Proton来运行Windows程序的GUI前端。

因Wine的获取安装较为复杂，于是我想到了使用Steam上的Proton来代替其功能，这样就有了更为便利的Wine安装和管理方式。

Steam本身也可以运行非Steam程序，但是启动比较麻烦，而且创建桌面方式经常失效，以及.desktop文件不显示应用图标等等问题。

于是我就让AI写了这个程序，可以做到利用Proton来启动Windows程序而不启动Steam，还可以生成带有图标的.desktop文件至桌面。

此应用100%使用TRAE AI的Qwen 3.6-Plus生成，请不放心使用。

目前程序还在测试状态，问题主要集中在用户页面上。

干杯！🍺

#### 构建
在终端运行以下命令即可打包为可执行文件：

    python3 build.py
