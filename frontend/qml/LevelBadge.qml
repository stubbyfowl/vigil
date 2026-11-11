StatusPill {
    property int level: 0
    status: level >= 3 ? "red" : level >= 1 ? "yellow" : "green"
    label: ["In range", "Level 1 · on board", "Level 2 · Medical Officer", "Level 3 · Earth"][level]
}
