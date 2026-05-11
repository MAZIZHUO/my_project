def is_prime(n):
    if n < 2:
        return False

    i = 2
    while i < n:
        if n % i == 0:
            return False  # return 的作用不仅是返回一个值，它还会强制退出当前所在的函数。一旦函数退出了，写在 return 后面的任何代码（包括 break）都相当于“死代码”（Dead Code），系统根本没机会去执行它。
        i += 1

    return True


def find_twin_primes(limit):
    twin_primes = []
    for n in range(2, limit):
        if is_prime(n) and is_prime(n + 2):
            twin_primes.append((n, n + 2))
    return twin_primes


if __name__ == "__main__":
    limit = 100
    twins = find_twin_primes(limit)
    print(f"100以内的孪生质数有 {len(twins)} 对:")
    for pair in twins:
        print(pair)
