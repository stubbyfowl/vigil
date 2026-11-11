pragma Singleton
import QtQuick

QtObject {
    // Mission Control is always dark. Everything else follows the chosen theme. Mission (dark) is the default.
    readonly property string mode: forceTheme || (vigil.route === "/ground" ? "dark" : vigil.theme)
    readonly property var p: vigil.palettes[mode]
    readonly property bool isLight: mode === "light"
    readonly property color bg: p.bg
    readonly property color panel: p.panel
    readonly property color panel2: p.panel2
    readonly property color glassFill: p.panel
    readonly property color glassFill2: p.panel2
    readonly property color rule: p.rule
    readonly property color ink: p.ink
    readonly property color ink2: p.ink2
    readonly property color band: p.band
    readonly property color link: p.link
    readonly property color action: p.action
    readonly property color actionEnd: p.actionEnd
    readonly property color actionText: p.actionText
    readonly property color urgent: p.urgent
    readonly property color urgentText: p.urgentText
    readonly property color nominal: p.nominal
    readonly property color nominalBg: p.nominalBg
    readonly property color caution: p.caution
    readonly property color cautionBg: p.cautionBg
    readonly property color warning: p.warning
    readonly property color warningBg: p.warningBg
    readonly property color flag: p.flag
    readonly property color shadow: p.shadow
    readonly property bool stars: p.stars
    // Type, after nasa.gov: Inter for headlines, Public Sans for reading, DM Mono for labels.
    readonly property string display: "Inter"
    readonly property string body: "Public Sans"
    readonly property string mono: "DM Mono"
    readonly property int touch: 56
    readonly property int gutter: 40
    readonly property int radius: 6
    readonly property int controlRadius: 4

    function statusColor(s) { return s === "green" ? nominal : s === "yellow" ? caution : warning }
    function statusFill(s) { return s === "green" ? nominalBg : s === "yellow" ? cautionBg : warningBg }
    function statusWord(s) { return s === "green" ? "Normal" : s === "yellow" ? "Drifting" : "Alert" }
    function faint(c, a) { return Qt.rgba(c.r, c.g, c.b, a) }
    function lead(text) { var i = text.indexOf(". "); return i < 0 ? text : text.slice(0, i + 1) }
    function rest(text) { var i = text.indexOf(". "); return i < 0 ? "" : text.slice(i + 2) }
}
