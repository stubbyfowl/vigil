StatusPill {
    property int level: 0
    status: level >= 3 ? "red" : level >= 1 ? "yellow" : "green"
    label: ["Clear", "Level 1: self-care", "Level 2: tell the Medical Officer", "Level 3: call Earth"][level]
}
