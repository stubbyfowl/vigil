import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: screen
    property var values: ({})
    property var saved: null
    property string errorText: ""
    readonly property var scales: [
        { key: "mood", label: "Mood", low: 1, high: 10, hint: "1 is very low, 10 is great" },
        { key: "sleep_quality", label: "Sleep", low: 1, high: 10, hint: "1 is very poor, 10 is great" },
        { key: "energy", label: "Energy", low: 1, high: 10, hint: "1 is empty, 10 is full" },
        { key: "stress", label: "Stress", low: 1, high: 10, hint: "1 is calm, 10 is extreme" },
        { key: "symptoms", label: "Symptoms", low: 0, high: 5, hint: "0 is none, 5 is severe" }
    ]
    readonly property var missing: scales.filter(function (s) { return values[s.key] === undefined }).map(function (s) { return s.label })

    function choose(key, value) {
        var copy = Object.assign({}, values)
        copy[key] = value
        values = copy
    }
    function save() {
        var result = Api.ask("checkin", Object.assign({ astronaut: vigil.astronaut, journal: journal.text, keep_text: keep.checked }, values))
        if (result.error) errorText = result.error
        else saved = result
    }

    ColumnLayout {
        anchors.fill: parent
        visible: screen.saved !== null
        spacing: 16
        Item { Layout.preferredHeight: 60 }
        BigTitle { Layout.alignment: Qt.AlignHCenter; text: screen.saved ? "Check-in saved for day " + screen.saved.day : "" }
        Body {
            horizontalAlignment: Text.AlignHCenter
            text: screen.saved ? (journal.text ? "Journal tone score: " + screen.saved.journal_score + ". " : "No journal entry today. ") + (screen.saved.text_kept ? "Your words were kept on this computer." : "Your words were not stored. Only the score was.") : ""
        }
        VButton { Layout.alignment: Qt.AlignHCenter; kind: "primary"; text: "Back to home"; onClicked: vigil.navigate("/") }
        Item { Layout.fillHeight: true }
    }

    ColumnLayout {
        anchors.fill: parent
        visible: screen.saved === null
        spacing: 12
        RowLayout { spacing: 12; BackButton {} BigTitle { text: "Daily check-in" } }
        RowLayout {
            Layout.fillWidth: true
            spacing: 16
            Panel {
                Layout.preferredWidth: 780
                Layout.alignment: Qt.AlignTop
                title: "Tap one number on each line"
                Repeater {
                    model: screen.scales
                    RowLayout {
                        required property var modelData
                        spacing: 4
                        Accessible.role: Accessible.Grouping
                        Accessible.name: modelData.label + ". " + modelData.hint + "."
                        Placard { text: modelData.label; font.pixelSize: 19; color: Theme.ink; Layout.preferredWidth: 110 }
                        Repeater {
                            model: parent.modelData.high - parent.modelData.low + 1
                            VButton {
                                required property int index
                                readonly property var spec: parent.modelData
                                readonly property int number: spec.low + index
                                text: number
                                textSize: 21
                                implicitWidth: Theme.touch
                                selected: screen.values[spec.key] === number
                                Accessible.name: spec.label + " " + number
                                onClicked: screen.choose(spec.key, number)
                            }
                        }
                    }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: 12
                Panel {
                    Layout.fillWidth: true
                    title: "Journal (optional)"
                    Note { text: "Scored on this computer with a word list. Nothing leaves it." }
                    TextArea {
                        id: journal
                        objectName: "journal"
                        Layout.fillWidth: true
                        Layout.preferredHeight: 150
                        wrapMode: TextEdit.Wrap
                        font.family: Theme.body
                        font.pixelSize: 18
                        color: Theme.ink
                        Accessible.name: "Journal"
                        background: Rectangle { color: Theme.panel2; border.color: journal.activeFocus ? Theme.action : "transparent"; radius: 10 }
                        onTextChanged: if (text.length > 2000) remove(2000, text.length)
                    }
                    RowLayout {
                        visible: vigil.voiceAvailable
                        Layout.fillWidth: true
                        spacing: 12
                        VButton { text: vigil.voiceListening ? "Stop" : "Speak"; kind: vigil.voiceListening ? "primary" : "normal"; onClicked: vigil.voiceToggle() }
                        Note { text: vigil.voiceHeard || (vigil.voiceListening ? "Listening." : "Speech becomes text here. Audio is never saved.") }
                    }
                    Connections {
                        target: vigil
                        function onVoiceFinal(text) { journal.text = (journal.text + " " + text).trim() }
                    }
                    Toggle { id: keep; text: "Keep my words on this computer" }
                }
                VButton { Layout.fillWidth: true; kind: "primary"; text: "Save check-in"; enabled: screen.missing.length === 0; onClicked: screen.save() }
                Note { visible: screen.missing.length > 0; text: "Still needed: " + screen.missing.join(", ") }
                Body { visible: screen.errorText.length > 0; text: screen.errorText; color: Theme.warning }
            }
        }
        Item { Layout.fillHeight: true }
    }
}
