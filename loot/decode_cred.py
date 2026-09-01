import sys, base64

data = base64.b64decode(sys.stdin.read().strip())
print("长度:", len(data))

# 看前50字节
for i in range(min(50, len(data))):
    c = chr(data[i]) if 32 <= data[i] < 127 else '.'
    print(f"  [{i:3d}] 0x{data[i]:02x} {c}")

# 搜 a1. 和 eyJ 模式
for i in range(len(data) - 3):
    if data[i:i+3] == b"a1.":
        print(f"找到 a1. 在偏移 {i}: {data[i:i+90]}")
    if data[i:i+3] in (b"eyJ", b"ey0"):
        print(f"找到 JWT 在偏移 {i}: {data[i:i+90]}")
    if data[i:i+5] == b"ck0.":
        print(f"找到 creditkey 在偏移 {i}: {data[i:i+90]}")

# 尝试 protobuf 解析
import struct
# 看前几个字段的 wire type
print("\n=== 尝试 protobuf 解析 ===")
pos = 0
while pos < len(data) and pos < 200:
    if data[pos] == 0:
        break
    field_num = data[pos] >> 3
    wire_type = data[pos] & 0x07
    print(f"  offset {pos}: field={field_num}, wire_type={wire_type}")
    if wire_type == 0:  # varint
        pos += 1
        while data[pos] & 0x80:
            pos += 1
        pos += 1
    elif wire_type == 2:  # length-delimited
        if pos + 1 >= len(data):
            break
        length = data[pos + 1]
        start = pos + 2
        end = start + length
        print(f"    length={length}, data={data[start:end]}")
        pos = end
    else:
        break