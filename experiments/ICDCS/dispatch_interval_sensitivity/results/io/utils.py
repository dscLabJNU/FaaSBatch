import platform



def get_data_path(path_mac, path_linux):
    MACOS = "macOS"
    LINUX = "Linux"
    platform_info = platform.platform()
    if MACOS in platform_info:
        PATH = path_mac
    elif LINUX in platform_info:
        PATH = path_linux
    return PATH