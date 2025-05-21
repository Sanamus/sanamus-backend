def multiplication_or_sum(num1, num2):
    product = num1 * num2
    if product <= 1000:
        return product
    else:
        return num1 + num2


result = multiplication_or_sum(20, 30)
print("the result is", result)

result = multiplication_or_sum(15, 45)
print("the result is", result)

result = multiplication_or_sum(50, 30)
print("the result is", result)
