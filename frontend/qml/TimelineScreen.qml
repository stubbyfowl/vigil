import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Item {
    id: screen
    readonly property var d: Api.ask("timeline", { v: vigil.version })
    readonly property var systemKeys: Object.keys(d.systems)
    readonly property int labelWidth: 56
    readonly property var codes: ({ g: "green", y: "yellow", r: "red" })

    function worst(person, day) {
        var rank = { g: 0, y: 1, r: 2 }, out = "g"
        systemKeys.forEach(function (k) { if (rank[person.status[k][day]] > rank[out]) out = person.status[k][day] })
        return out
    }
    function percent(day) { return (day - 1) / (d.mission_days - 1) }

    PageScroll {
        anchors.fill: parent
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            BackButton {}
            BigTitle { text: "Mission day " + vigil.day }
            Item { Layout.fillWidth: true }
            VButton { text: vigil.running ? "Pause" : "Play mission"; onClicked: Api.ask("set_clock", { running: !vigil.running }) }
        }
        Panel {
            Layout.fillWidth: true
            surface: true
            Item {
                id: markers
                Layout.fillWidth: true
                Layout.leftMargin: screen.labelWidth
                implicitHeight: 60
                Repeater {
                    model: screen.d.events
                    AbstractButton {
                        required property var modelData
                        x: screen.percent(modelData.day) * markers.width - width / 2
                        anchors.bottom: parent.bottom
                        implicitWidth: Math.max(Theme.touch, mark.implicitWidth + 16)
                        implicitHeight: Theme.touch
                        Accessible.role: Accessible.Button
                        Accessible.name: "Jump to " + modelData.title + ", day " + modelData.day
                        onClicked: Api.ask("set_clock", { day: modelData.day, running: false })
                        background: Rectangle { anchors { left: parent.left; right: parent.right; bottom: parent.bottom } height: 2; radius: 1; color: Theme.flag }
                        contentItem: Placard { id: mark; text: modelData.title; color: Theme.ink; font.pixelSize: 18; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }
                }
            }
            Item {
                id: lanes
                Layout.fillWidth: true
                implicitHeight: screen.d.crew.length * 25
                Repeater {
                    model: screen.d.crew
                    Placard { required property var modelData; required property int index; y: index * 25; text: modelData.tag }
                }
                Canvas {
                    id: laneCanvas
                    objectName: "lanes"
                    x: screen.labelWidth
                    width: parent.width - screen.labelWidth
                    height: parent.height
                    Accessible.role: Accessible.Graphic
                    Accessible.name: "Health status of each crew member across the whole mission."
                    Connections { target: screen; function onDChanged() { laneCanvas.requestPaint() } }
                    Connections { target: Theme; function onModeChanged() { laneCanvas.requestPaint() } }
                    onWidthChanged: requestPaint()
                    onPaint: {
                        var c = getContext("2d")
                        c.reset()
                        var cell = width / screen.d.mission_days
                        var color = { g: Theme.panel2, y: Theme.p.ribbonWarm[0], r: Theme.p.ribbonWarm[1] }
                        screen.d.crew.forEach(function (person, row) {
                            for (var day = 0; day < screen.d.mission_days; day++) {
                                c.fillStyle = color[screen.worst(person, day)]
                                c.fillRect(day * cell, row * 25, cell + 0.5, 22)
                            }
                        })
                    }
                }
                Rectangle {
                    x: screen.labelWidth + screen.percent(vigil.day) * laneCanvas.width
                    y: -4
                    width: 2
                    height: parent.height + 8
                    color: Theme.ink
                }
            }
            Slider {
                id: scrubber
                objectName: "scrubber"
                Layout.fillWidth: true
                Layout.leftMargin: screen.labelWidth
                implicitHeight: Theme.touch
                from: 1
                to: screen.d.mission_days
                stepSize: 1
                snapMode: Slider.SnapAlways
                value: vigil.day
                Accessible.name: "Mission day"
                onMoved: Api.ask("set_clock", { day: Math.round(value), running: false })
                background: Rectangle { x: scrubber.leftPadding; y: (scrubber.height - height) / 2; width: scrubber.availableWidth; height: 6; radius: 3; color: Theme.panel2 }
                handle: Item {
                    x: scrubber.leftPadding + scrubber.visualPosition * (scrubber.availableWidth - width)
                    y: 0
                    width: Theme.touch
                    height: Theme.touch
                    Rectangle {
                        anchors.centerIn: parent
                        width: 30
                        height: 30
                        radius: 15
                        color: Theme.action
                        border.color: scrubber.visualFocus ? Theme.ink : Theme.panel
                        border.width: 3
                    }
                }
            }
        }
        Panel {
            Layout.fillWidth: true
            GridLayout {
                Layout.fillWidth: true
                columns: screen.systemKeys.length + 2
                columnSpacing: 8
                rowSpacing: 6
                Placard { text: "Crew on day " + vigil.day; Layout.preferredWidth: 150 }
                Repeater { model: screen.systemKeys; Placard { required property string modelData; text: screen.d.systems[modelData]; Layout.fillWidth: true; Layout.preferredWidth: 1; elide: Text.ElideRight } }
                Placard { text: "Level"; Layout.preferredWidth: 60 }
                Repeater {
                    model: screen.d.crew.length * (screen.systemKeys.length + 2)
                    Loader {
                        required property int index
                        readonly property int columns: screen.systemKeys.length + 2
                        readonly property var person: screen.d.crew[Math.floor(index / columns)]
                        readonly property int column: index % columns
                        Layout.fillWidth: column > 0 && column < columns - 1
                        Layout.preferredWidth: column > 0 && column < columns - 1 ? 1 : -1
                        sourceComponent: column === 0 ? nameCell : column === columns - 1 ? levelCell : statusCell
                    }
                }
            }
            Component { id: nameCell; Body { text: parent.person.name; font.weight: Font.DemiBold } }
            Component { id: levelCell; Text { text: parent.person.level[vigil.day - 1] || "None"; font.family: Theme.body; font.features: { "tnum": 1 }; font.pixelSize: 18; color: Theme.ink } }
            Component { id: statusCell; StatusPill { compact: true; status: screen.codes[parent.person.status[screen.systemKeys[parent.column - 1]][vigil.day - 1]] } }
        }
    }
}
