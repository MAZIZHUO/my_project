from functions import get_formatted_name

# 使用pytest测试函数，pytest会自动运行以test_开头的函数，并检查断言是否为真。


def test_get_formatted_name():
    """测试get_formatted_name()函数"""
    formatted_name = get_formatted_name("janis", "joplin")
    assert formatted_name == "Janis Joplin"
    formatted_name = get_formatted_name("jimi", "hendrix")
    assert formatted_name == "Jimi Hendrix"


def test_get_formatted_name_middle():
    """测试get_formatted_name()函数，包含中间名"""
    formatted_name = get_formatted_name("john", "hooker")
    assert formatted_name == "John Hooker"
    formatted_name = get_formatted_name("john", "hooker", "lee")
    assert formatted_name == "John Lee Hooker"


if __name__ == "__main__":
    test_get_formatted_name()
    test_get_formatted_name_middle()
    print("所有测试都通过！")
