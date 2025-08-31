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
    write_to_save_file(number,4,num_write)
def increase_province_count():
    x = read_from_save_file(4, 4)
    x += 1
    update_province_number(x,4)
def create_save_file():
    m = 77
    g = 71
    s = 83
    control_data = [m, g, s, g]
    p = 0
    open("start_save.MGSG" , "wb").close()
    for i in control_data:
        write_to_save_file(i,p, 1)
        p += 1
def read_province_number():
    x = read_from_save_file(4 , 4)
    return x
def write_new_province(province_id):
    new_province_offset = read_province_number()
    increase_province_count()
    p = 87
    write_offset = new_province_offset + 8
    write_to_save_file(p, write_offset,1)
    write_offset = new_province_offset + 9
    write_to_save_file(province_id , write_offset , 4)
    