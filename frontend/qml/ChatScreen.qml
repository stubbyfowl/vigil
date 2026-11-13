import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// The organ group chat, and texts from this person at 70. Under every message is the reading it came from.
Item {
    id: screen
    property string thread: "organs"
    readonly property var chat: Api.ask("organ_chat", { id: vigil.astronaut, day: vigil.day, v: vigil.version })
    readonly property var future: Api.ask("future_you", { id: vigil.astronaut, day: vigil.day, v: vigil.version })
    readonly property var messages: screen.thread === "organs" ? (chat.messages || []) : (future.texts || []).map(function (t) {
        return { tag: "70", name: "You, age 70", text: t.text, why: t.why, day: -1, time: "" }
    })
    readonly property var moodWord: ({ chill: "Chill", okay: "Okay", grumpy: "Grumpy", quiet: "Quiet" })

    function toBottom() { Qt.callLater(function () { var f = scroll.contentItem; f.contentY = Math.max(0, f.contentHeight - f.height) }) }
    onMessagesChanged: toBottom()
    Component.onCompleted: toBottom()

    PageScroll {
        id: scroll
        anchors.fill: parent
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            BackButton {}
            BigTitle { text: screen.thread === "organs" ? "Organ group chat" : "Texts from you at 70" }
            Item { Layout.fillWidth: true }
            VButton { text: "Organs"; selected: screen.thread === "organs"; onClicked: screen.thread = "organs" }
            VButton { text: "You at 70"; selected: screen.thread === "future"; onClicked: screen.thread = "future" }
        }
        Banner { tone: "error"; text: screen.chat.error || screen.future.error || "" }
        Note {
            Layout.maximumWidth: 820
            text: screen.thread === "organs"
                ? "Each organ texts about one of your readings from the last 7 days, and the line under each message is that reading. These are jokes, not medical advice."
                : "Written from your last " + (screen.future.days || 14) + " days of exercise, sleep, stress, social time and bone marker. Not a prediction."
        }
        // Who is in the chat.
        Flow {
            visible: screen.thread === "organs"
            Layout.fillWidth: true
            spacing: 14
            Repeater {
                model: screen.chat.organs || []
                Row {
                    required property var modelData
                    spacing: 8
                    Avatar { size: 32; initials: modelData.tag; anchors.verticalCenter: parent.verticalCenter }
                    Note { text: modelData.name; anchors.verticalCenter: parent.verticalCenter }
                }
            }
        }
        RowLayout {
            visible: screen.thread === "future" && !!screen.future.mood
            spacing: 12
            Avatar { size: 48; initials: "70" }
            Body { Layout.fillWidth: false; text: "You, age 70"; font.weight: Font.DemiBold }
            StatusPill {
                compact: true
                status: screen.future.mood === "grumpy" ? "red" : screen.future.mood === "okay" ? "yellow" : "green"
                label: "Mood: " + (screen.moodWord[screen.future.mood] || "")
            }
        }
        Banner { visible: screen.messages.length === 0; text: screen.thread === "organs" ? "No messages yet. The organs start talking once there are readings." : "Not enough readings yet for a text from future you." }

        Repeater {
            model: screen.messages
            ColumnLayout {
                id: message
                required property var modelData
                required property int index
                readonly property bool newDay: modelData.day > 0 && (index === 0 || screen.messages[index - 1].day !== modelData.day)
                Layout.fillWidth: true
                spacing: 6
                Placard { visible: message.newDay; Layout.topMargin: 14; text: "Day " + message.modelData.day }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    Avatar { size: 44; initials: message.modelData.tag; Layout.alignment: Qt.AlignTop }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        RowLayout {
                            spacing: 10
                            Text { text: message.modelData.name; font.family: Theme.display; font.weight: Font.DemiBold; font.pixelSize: 16; color: Theme.ink }
                            Note { Layout.fillWidth: false; text: message.modelData.time }
                        }
                        Rectangle {
                            Layout.preferredWidth: Math.min(words.implicitWidth + 32, 640)
                            Layout.maximumWidth: 640
                            implicitHeight: words.implicitHeight + 24
                            radius: 14
                            color: Theme.panel
                            border.width: 1
                            border.color: Theme.rule
                            Text {
                                id: words
                                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; leftMargin: 16; rightMargin: 16 }
                                text: message.modelData.text
                                wrapMode: Text.WordWrap
                                font.family: Theme.body
                                font.pixelSize: 18
                                color: Theme.ink
                            }
                        }
                        Note { visible: !!message.modelData.why; Layout.maximumWidth: 640; text: message.modelData.why; font.pixelSize: 13 }
                    }
                }
            }
        }
    }
}
