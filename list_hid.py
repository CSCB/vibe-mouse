"""临时脚本：枚举系统 HID 设备，定位激光笔 VID/PID"""
import hid

devices = hid.enumerate()
print(f"Total HID devices: {len(devices)}")
for d in devices:
    print(
        f"VID={d['vendor_id']:04x} PID={d['product_id']:04x} | "
        f"mfr={d['manufacturer_string']!r:25} | prod={d['product_string']!r:25} | "
        f"usage_page={d['usage_page']:04x} usage={d['usage']:04x}"
    )
