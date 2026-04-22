import random
 
hour = random.randint(20, 21)
minute = random.randint(0, 59)
second = random.randint(0, 59)
 
print(f"{hour:02d}:{minute:02d}:{second:02d}")