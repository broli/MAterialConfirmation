from PIL import Image

icon_sizes = [
    Image.open("Icon_512.png"),
    Image.open("Icon_128.png"),
    Image.open("Icon_64.png"),
]

icon_sizes[0].save('app_icon.ico', format='ICO', append_images=icon_sizes[1:])