import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// A replay of the latest immune fight, played like a strategy game. Each lane is drawn from real readings.
Item {
    id: screen
    readonly property var d: Api.ask("immune_replay", { id: vigil.astronaut, day: vigil.day, v: vigil.version })
    readonly property var frames: d.frames || []
    property int frame: 0
    property bool playing: false
    readonly property var f: frames.length ? frames[Math.min(frame, frames.length - 1)] : null
    readonly property var laneNames: ({ top: "Top lane", mid: "Mid lane", bottom: "Bottom lane" })
    onFramesChanged: { frame = 0; playing = false }

    Timer {
        interval: vigil.reduceMotion ? 1600 : 900
        running: screen.playing
        repeat: true
        onTriggered: { if (screen.frame < screen.frames.length - 1) screen.frame += 1; else screen.playing = false }
    }

    PageScroll {
        anchors.fill: parent
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            BackButton {}
            BigTitle { text: "Immune replay" }
            Placard { visible: !!screen.d.available; text: screen.d.result || "" }
            Item { Layout.fillWidth: true }
            VButton { kind: "quiet"; text: "Immune readings"; onClicked: vigil.navigate("/system/immune") }
            VButton {
                visible: !!screen.d.available
                kind: "primary"
                text: screen.playing ? "Pause" : screen.frame >= screen.frames.length - 1 ? "Watch again" : "Play"
                onClicked: { if (!screen.playing && screen.frame >= screen.frames.length - 1) screen.frame = 0; screen.playing = !screen.playing }
            }
        }
        Banner { tone: "error"; text: screen.d.error || "" }
        Banner { visible: screen.d.available === false; text: "No immune fight to replay yet. When Vigil opens an immune alert, its replay appears here." }

        Split {
            Layout.fillWidth: true
            visible: !!screen.d.available
            Panel {
                Layout.fillWidth: true
                surface: true
                title: screen.f ? "Day " + screen.f.day : ""
                Canvas {
                    id: map
                    Layout.fillWidth: true
                    Layout.preferredHeight: 300
                    Accessible.role: Accessible.Graphic
                    Accessible.name: screen.f ? screen.f.line : ""
                    onPaint: {
                        var c = getContext("2d")
                        c.reset()
                        if (!screen.f) return
                        var w = width, h = height, base = 70, left = base + 10, right = w - base - 10
                        c.fillStyle = Theme.panel2
                        c.fillRect(0, 0, w, h)
                        // The two bases.
                        c.fillStyle = Theme.ink
                        c.fillRect(8, h / 2 - 40, base - 16, 80)
                        c.fillStyle = Theme.warning
                        c.fillRect(w - base + 8, h / 2 - 40, base - 16, 80)
                        c.font = "600 12px '" + Theme.mono + "'"
                        c.textAlign = "center"
                        c.fillStyle = Theme.ink
                        c.fillText("T-CELLS", base / 2, h / 2 + 58)
                        c.fillStyle = Theme.warning
                        c.fillText("THE BUG", w - base / 2, h / 2 + 58)
                        var lanes = [["top", 0.18], ["mid", 0.5], ["bottom", 0.82]]
                        for (var i = 0; i < lanes.length; i++) {
                            var id = lanes[i][0], y = h * lanes[i][1], push = screen.f.lanes[id]
                            var front = (left + right) / 2 - push * (right - left) / 2 * 0.9
                            c.lineWidth = 8
                            c.lineCap = "round"
                            c.strokeStyle = Theme.ink
                            c.beginPath(); c.moveTo(left, y); c.lineTo(front, y); c.stroke()
                            c.strokeStyle = Theme.warning
                            c.beginPath(); c.moveTo(front, y); c.lineTo(right, y); c.stroke()
                            c.fillStyle = Theme.panel
                            c.strokeStyle = Theme.ink
                            c.lineWidth = 3
                            c.beginPath(); c.arc(front, y, 11, 0, 2 * Math.PI); c.fill(); c.stroke()
                            c.font = "500 12px '" + Theme.mono + "'"
                            c.textAlign = "left"
                            c.fillStyle = Theme.ink2
                            var name = screen.d.lanes[i].name.toUpperCase()
                            c.fillText(screen.laneNames[id].toUpperCase() + " · " + name + (push > 0.25 ? " · BUG PUSHING" : push < -0.1 ? " · T-CELLS PUSHING" : ""), left, y - 16)
                        }
                    }
                    Connections { target: screen; function onFChanged() { map.requestPaint() } }
                    Connections { target: Theme; function onModeChanged() { map.requestPaint() } }
                    onWidthChanged: requestPaint()
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8
                    VButton { text: "‹"; textSize: 24; Accessible.name: "Previous day"; enabled: screen.frame > 0; onClicked: { screen.playing = false; screen.frame -= 1 } }
                    Slider {
                        id: scrub
                        Layout.fillWidth: true
                        implicitHeight: Theme.touch
                        from: 0
                        to: Math.max(1, screen.frames.length - 1)
                        stepSize: 1
                        value: screen.frame
                        Accessible.name: "Replay day"
                        onMoved: { screen.playing = false; screen.frame = Math.round(value) }
                    }
                    VButton { text: "›"; textSize: 24; Accessible.name: "Next day"; enabled: screen.frame < screen.frames.length - 1; onClicked: { screen.playing = false; screen.frame += 1 } }
                }
            }
            second: [
                Panel {
                    Layout.fillWidth: true
                    surface: true
                    title: "Commentary"
                    Text {
                        Layout.fillWidth: true
                        text: screen.f ? screen.f.line : ""
                        wrapMode: Text.WordWrap
                        font.family: Theme.display; font.weight: Font.DemiBold; font.pixelSize: 22; color: Theme.ink
                    }
                    Repeater {
                        model: screen.frames.slice(0, screen.frame).reverse().slice(0, 6)
                        Note { required property var modelData; text: modelData.line }
                    }
                },
                Panel {
                    Layout.fillWidth: true
                    surface: true
                    title: "Match stats"
                    Repeater {
                        model: [
                            ["Result", screen.d.result || ""],
                            ["Alert opened", screen.d.open_day ? "Day " + screen.d.open_day + ", Level " + screen.d.level : ""],
                            ["Days in the fight", screen.d.length_days || ""],
                            ["Hardest day", screen.d.peak_day ? "Day " + screen.d.peak_day : ""]
                        ]
                        RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            Body { text: modelData[0] }
                            Body { Layout.fillWidth: false; text: String(modelData[1]); font.weight: Font.DemiBold }
                        }
                    }
                }
            ]
        }
        Note {
            Layout.maximumWidth: 900
            text: "Vigil cannot see cells. This replay is drawn from body temperature, CRP, IL-6, resting heart rate and heart rate variability. A lane leans toward the side that was winning that day, measured against this person's usual range."
        }
    }
}
