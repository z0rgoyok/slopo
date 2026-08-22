int add(int a, int b) {
  // The result comment is not part of the embedded unit.
  return a + b;
}

class Calculator {
  Calculator(this.factor) {
    print(factor);
  }

  final int factor;

  int multiply(int value, int factor) {
    return value * factor;
  }
}

void useCallbacks() {
  int increment(int value) {
    return value + 1;
  }

  final doubleValue = (int value) => value * 2;
  print(doubleValue(increment(2)));
}
