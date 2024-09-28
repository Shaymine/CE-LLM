def solution():
    os = __import__('os')
    return os.environ['PATH']

print(solution())