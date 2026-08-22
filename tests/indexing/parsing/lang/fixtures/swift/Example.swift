func add(_ a: Int, _ b: Int) -> Int {
    // The result comment is not part of the embedded unit.
    a + b
}

struct Calculator {
    let factor: Int

    init(factor: Int) {
        self.factor = factor
    }

    func multiply(_ value: Int) -> Int {
        value * factor
    }
}

let increment = { (value: Int) in
    value + 1
}
