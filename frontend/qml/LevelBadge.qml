Annunciator {
    property int level: 0
    status: level >= 3 ? "red" : level >= 1 ? "yellow" : "green"
    label: ["Clear", "Level 1 · Self-care", "Level 2 · Tell Medical Officer", "Level 3 · Call Earth"][level]
}
