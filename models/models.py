class Counters:
    def __init__(self):
        self.count = 0
        self.ignored_count = 0
        self.error_count = 0

    def increment_count(self):
        self.count += 1

    def increment_ignored_count(self):
        self.ignored_count += 1

    def increment_error_count(self):
        self.error_count += 1