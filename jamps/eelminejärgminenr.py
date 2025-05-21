print("print previous nr and current nr and their sum i a range(10)")
previous_num = 0

for i in range(1, 11):
    x_sum = previous_num + i
    print("Current nr", i, "previous nr", previous_num, "sum:", x_sum)
    previous_num = i
