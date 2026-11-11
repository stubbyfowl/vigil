import QtQuick
import QtQuick.Layouts

// A quiet status surface for messages that stay. Meaning is carried by an icon and words, not color alone.
Rectangle {
    id: banner
    property string tone: "info"   // info, success, caution, error
    property string text: ""
    property string action: ""
    signal actionClicked
    readonly property string status: tone === "success" ? "green" : tone === "caution" ? "yellow" : tone === "error" ? "red" : ""
    Layout.fillWidth: true
    visible: text.length > 0
    radius: 12
    color: status ? Theme.statusFill(status) : Theme.panel2
    implicitHeight: Math.max(Theme.touch, row.implicitHeight + 20)
    Accessible.role: Accessible.AlertMessage
    Accessible.name: text

    RowLayout {
        id: row
        anchors { fill: parent; leftMargin: 16; rightMargin: 8 }
        spacing: 12
        StatusIcon { visible: banner.status.length > 0; status: banner.status; tint: Theme.statusColor(banner.status) }
        Text { visible: !banner.status; text: "i"; font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 18; color: Theme.ink2 }
        Body { text: banner.text; Layout.fillWidth: true }
        VButton { visible: banner.action.length > 0; text: banner.action; kind: "quiet"; onClicked: banner.actionClicked() }
    }
}
