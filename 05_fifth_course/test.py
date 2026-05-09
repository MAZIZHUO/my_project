def gender():
    sex = input("请输入性别：")
    if sex == "男":
        print("你是一个男性")
    elif sex == "女":
        print("你是一个女性")
    else:
        raise Exception("输入错误，请输入男或女")
        print("这是一个测试代码")
