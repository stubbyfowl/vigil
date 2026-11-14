import QtQuick
import QtQuick.Layouts

// Each mission month is an album and each week a track, made on this computer from that week's readings.
Item {
    id: screen
    property int month: 0  // 0 means the latest month
    property int playingNumber: 0
    property string error: ""
    readonly property var d: Api.ask("album", screen.month > 0 ? { id: vigil.astronaut, month: screen.month, day: vigil.day, v: vigil.version } : { id: vigil.astronaut, day: vigil.day, v: vigil.version })
    readonly property var tracks: d.tracks || []
    readonly property string mostly: {
        var count = {}, best = ""
        tracks.forEach(function (t) { count[t.style] = (count[t.style] || 0) + 1; if (!best || count[t.style] > count[best]) best = t.style })
        return best
    }

    function play(t) {
        var r = Api.ask("album_track", { id: vigil.astronaut, month: screen.d.month, number: t.number, day: vigil.day })
        if (r.error) { screen.error = r.error; return }
        screen.error = vigil.playTrack(r.path)
        screen.playingNumber = screen.error ? 0 : t.number
    }

    PageScroll {
        anchors.fill: parent
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            BackButton {}
            BigTitle { text: "Heart rate album" }
            Item { Layout.fillWidth: true }
            VButton { kind: "quiet"; text: "Heart readings"; onClicked: vigil.navigate("/system/heart") }
        }
        // One album per mission month. Wraps onto more lines as the mission goes on.
        Flow {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: screen.d.months || 0
                VButton {
                    required property int index
                    text: "Month " + (index + 1)
                    selected: screen.d.month === index + 1
                    onClicked: { vigil.stopTrack(); screen.month = index + 1 }
                }
            }
        }
        Banner { tone: "error"; text: screen.d.error || screen.error }
        Banner { visible: !vigil.canPlay; text: "No audio player was found on this computer. Tracks are still saved as WAV files in the exports folder." }

        RowLayout {
            Layout.fillWidth: true
            spacing: 28
            Canvas {
                id: cover
                Layout.preferredWidth: 240
                Layout.preferredHeight: 240
                Layout.alignment: Qt.AlignTop
                Accessible.role: Accessible.Graphic
                Accessible.name: "Album cover drawn from " + screen.tracks.length + " weeks of readings"
                onPaint: {
                    var c = getContext("2d")
                    c.reset()
                    c.fillStyle = Theme.panel2
                    c.fillRect(0, 0, width, height)
                    var cx = width / 2, cy = height / 2
                    for (var i = 0; i < screen.tracks.length; i++) {
                        var t = screen.tracks[i]
                        c.strokeStyle = t.style === "Drum and bass" ? Theme.link : Theme.ink
                        c.globalAlpha = t.style === "Lo-fi" ? 0.55 : 1
                        c.lineWidth = 4 + (t.tempo - 50) / 12
                        if (t.style === "Drum and bass") c.setLineDash([2, 3]); else c.setLineDash([])
                        c.beginPath()
                        c.arc(cx, cy, 26 + i * 24, -Math.PI / 2, -Math.PI / 2 + 2 * Math.PI * Math.min(1, t.sleep / 8))
                        c.stroke()
                    }
                    c.globalAlpha = 1
                    c.setLineDash([])
                    c.fillStyle = Theme.ink
                    c.font = "800 22px '" + Theme.display + "'"
                    c.textAlign = "center"
                    c.fillText("M" + (screen.d.month || ""), cx, cy + 8)
                }
                Connections { target: screen; function onTracksChanged() { cover.requestPaint() } }
                Connections { target: Theme; function onModeChanged() { cover.requestPaint() } }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignTop
                spacing: 10
                Statement {
                    Layout.fillWidth: true
                    size: 32
                    lead: screen.tracks.length ? "Month " + screen.d.month + ", mostly " + screen.mostly.toLowerCase() + "." : "No tracks yet."
                    detail: screen.tracks.length ? "Days " + screen.d.first_day + " to " + screen.d.last_day + ". One track per week." : "A track needs at least three days of heart rate readings in a week."
                }
                Note {
                    text: "Calm weeks are lo-fi at your resting heart rate. Stressful weeks, or weeks with drift, are drum and bass at about three times it. Each hour of sleep adds 4 seconds, higher heart rate variability makes a busier melody, and a good mood picks a major key. Vigil has no breathing data, so breathing is not part of it."
                }
            }
        }

        Panel {
            Layout.fillWidth: true
            surface: true
            title: "Tracks"
            Repeater {
                model: screen.tracks
                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 16
                    Placard { Layout.preferredWidth: 28; text: modelData.number; font.pixelSize: 16 }
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Body { text: modelData.title + "  ·  " + modelData.style + ", " + modelData.tempo + " bpm"; font.weight: Font.DemiBold }
                        Note {
                            text: "Days " + modelData.first_day + " to " + modelData.last_day + ". Resting heart rate " + modelData.heart_rate + " bpm, stress " + modelData.stress
                                  + " of 10, sleep " + modelData.sleep + " hours, " + modelData.seconds + " seconds long."
                        }
                    }
                    VButton {
                        readonly property bool mine: vigil.playing !== "" && screen.playingNumber === modelData.number
                        kind: mine ? "primary" : "normal"
                        text: mine ? "Stop" : "Play"
                        Accessible.name: (mine ? "Stop " : "Play ") + modelData.title
                        onClicked: mine ? vigil.stopTrack() : screen.play(modelData)
                    }
                }
            }
        }
        Note { text: "Tracks are made on this computer and saved in the exports folder, under album." }
    }
}
