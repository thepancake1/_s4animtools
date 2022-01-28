values = [796, 1009, 796]
offset = 0.444224
# Scale is inverted for some reason
scale = -0.570586
signs = [0, 1, 0]
idx = 0
for value in values:
    new_value = (value / 1023)
    if signs[idx]:
        new_value *= -1

    new_value = new_value * scale + offset
    print(new_value)
    idx += 1