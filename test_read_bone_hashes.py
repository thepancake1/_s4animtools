with open("bone_hashes.txt", "r") as file:
    for line in file.readlines():
        print('"{}"'.format(line.split(" ")[0]), end=",")