pragma Singleton
import QtQuick

QtObject {
    readonly property var p: vigil.palettes[vigil.theme]
    readonly property color bg: p.bg
    readonly property color panel: p.panel
    readonly property color panel2: p.panel2
    readonly property color rule: p.rule
    readonly property color ink: p.ink
    readonly property color ink2: p.ink2
    readonly property color band: p.band
    readonly property color action: p.action
    readonly property color onAction: p.onAction
    readonly property color nominal: p.nominal
    readonly property color caution: p.caution
    readonly property color warning: p.warning
    readonly property color onLit: p.onLit
    readonly property string body: "B612"
    readonly property string mono: "B612 Mono"
    readonly property string label: "Barlow Condensed SemiBold"
    readonly property int touch: 56
    readonly property int gutter: 20

    function statusColor(s) { return s === "green" ? nominal : s === "yellow" ? caution : warning }
    function statusWord(s) { return s === "green" ? "Nominal" : s === "yellow" ? "Watch" : "Act" }
}
