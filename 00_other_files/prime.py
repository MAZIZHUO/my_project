def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True


def find_twin_primes(limit):
    twin_primes = []
    for i in range(3, limit - 1):
        if is_prime(i) and is_prime(i + 2):
            twin_primes.append((i, i + 2))
    return twin_primes


if __name__ == "__main__":
    limit = 10000
    twins = find_twin_primes(limit)
    print(f"100以内的孪生质数有 {len(twins)} 对:")
    for pair in twins:
        print(pair)
