class NumberProcessor:
    def __init__(self, filename, output_filename):
        self.filename = filename
        self.output_filename = output_filename

    def process(self):
        with open(self.filename) as f:
            content = f.read()

        numbers = content.split(',')
        count = len(numbers)

        # Create a dictionary to count the occurrences of each number
        counts = {}
        for n in numbers:
            if n is not None:
                try:
                    n = float(n)
                    if n not in counts:
                        counts[n] = 1
                    else:
                        counts[n] += 1
                except ValueError:
                    pass

        # Sort the counts in descending order based on their frequency
        sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)

        with open(self.output_filename, 'w') as f:
            f.write(f"Count of numbers: {count}\n")
            f.write("Sorted numbers:\n")
            for num, freq in sorted_counts:
                f.write(f"{num}: {freq}\n")

if __name__ == '__main__':
    processor = NumberProcessor('artifacts/top-level-frame-size-stat.txt', 'artifacts/stat-width-sorted.txt')
    processor.process()
