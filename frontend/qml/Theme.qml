pragma Singleton
import QtQuick

QtObject {
    // Mission Control is always the dark control room. Everything else follows the chosen theme.
    readonly property string mode: forceTheme || (vigil.route === "/ground" ? "dark" : vigil.theme)
    readonly property var p: vigil.palettes[mode]
    readonly property bool isLight: mode === "light"
    readonly property color bg: p.bg
    readonly property color panel: p.panel
    readonly property color panel2: p.panel2
    readonly property color rule: p.rule
    readonly property color ink: p.ink
    readonly property color ink2: p.ink2
    readonly property color band: p.band
    readonly property color action: p.action
    readonly property color actionText: p.actionText
    readonly property color nominal: p.nominal
    readonly property color nominalBg: p.nominalBg
    readonly property color caution: p.caution
    readonly property color cautionBg: p.cautionBg
    readonly property color warning: p.warning
    readonly property color warningBg: p.warningBg
    readonly property color flag: p.flag
    readonly property color shadow: p.shadow
    readonly property string body: "Instrument Sans"
    readonly property int touch: 56
    readonly property int gutter: 40
    readonly property int radius: 14

    function statusColor(s) { return s === "green" ? nominal : s === "yellow" ? caution : warning }
    function statusFill(s) { return s === "green" ? nominalBg : s === "yellow" ? cautionBg : warningBg }
    function statusWord(s) { return s === "green" ? "Nominal" : s === "yellow" ? "Watch" : "Act" }
    function lead(text) { var i = text.indexOf(". "); return i < 0 ? text : text.slice(0, i + 1) }
    function rest(text) { var i = text.indexOf(". "); return i < 0 ? "" : text.slice(i + 2) }
}
