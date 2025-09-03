def write_to_save_file(x, s, num_write):
    with open("start_save.MGSG" , "rb+") as f:
        if s != -1:
            f.seek(s)
        f.write(x.to_bytes(num_write , "big"))
def read_from_save_file(s, num_read):
    with open("start_save.MGSG", "rb+") as f:
        if s != -1:
            f.seek(s)
        raw = f.read(num_read)
        x = int.from_bytes(raw , "big")
        return x
def update_province_number(number, num_write):
    write_to_save_file(number,5,num_write)
def increase_province_count():
    x = read_from_save_file(4, 4)
    x += 1
    update_province_number(x,4)
def create_save_file():
    control_data = [77, 71, 83, 71]
    p = 0
    open("start_save.MGSG" , "wb").close()
    for i in control_data:
        write_to_save_file(i,p, 1)
        p += 1