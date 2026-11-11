import QtQuick
import QtQuick.Layouts

Item {
    id: screen
    readonly property var d: Api.ask("radiation", { id: vigil.astronaut, day: vigil.day, v: vigil.version })
    readonly property bool active: d.storm.phase === "active"
    property bool drill: false
    function pct(v) { return Math.min(v / d.limit_msv, 1) }

    PageScroll {
        anchors.fill: parent
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            BackButton {}
            BigTitle { text: "Radiation" }
            StatusPill { status: screen.d.status }
            Item { Layout.fillWidth: true }
            VButton { visible: !screen.active; text: screen.drill ? "End drill" : "Storm drill"; onClicked: screen.drill = !screen.drill }
        }
        Statement {
            Layout.maximumWidth: 900
            size: 38
            lead: "Career dose: " + screen.d.career_dose_msv + " of " + screen.d.limit_msv + " mSv."
            detail: "At this rate it will be " + screen.d.projected_total_msv + " mSv when the mission ends."
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8
            Item {
                id: track
                Layout.fillWidth: true
                implicitHeight: 18
                Accessible.role: Accessible.ProgressBar
                Accessible.name: "Career dose " + screen.d.career_dose_msv + " of " + screen.d.limit_msv + " millisieverts. Projected " + screen.d.projected_total_msv + "."
                Rectangle { anchors.fill: parent; radius: 9; color: Theme.panel2 }
                Rectangle { width: track.width * screen.pct(screen.d.projected_total_msv); height: parent.height; radius: 9; color: Theme.band; opacity: 0.3 }
                Rectangle { width: track.width * screen.pct(screen.d.career_dose_msv); height: parent.height; radius: 9; color: Theme.action }
                Rectangle { width: track.width * screen.pct(screen.d.prior_dose_msv); height: parent.height; radius: 9; color: Theme.ink }
            }
            RowLayout {
                Layout.fillWidth: true
                Note { Layout.fillWidth: false; text: "Before this mission " + screen.d.prior_dose_msv }
                Item { Layout.fillWidth: true }
                Note { Layout.fillWidth: false; text: "This mission " + screen.d.mission_dose_msv }
                Item { Layout.fillWidth: true }
                Note { Layout.fillWidth: false; text: "Limit " + screen.d.limit_msv + " mSv" }
            }
        }
        Split {
            Layout.fillWidth: true
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Repeater {
                    model: [["Today", screen.d.today_dose_msv, "mSv"], ["Dose rate", screen.d.dose_rate_usv_h, "uSv per hour"], ["At mission end", screen.d.projected_total_msv, "mSv career total"]]
                    Panel {
                        required property var modelData
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        divider: true
                        title: modelData[0]
                        Text { text: modelData[1] === null ? "No reading" : modelData[1]; font.family: Theme.body; font.weight: Font.Medium; font.pixelSize: 34; font.letterSpacing: -1; font.features: { "tnum": 1 }; color: Theme.ink }
                        Note { text: modelData[2] }
                    }
                }
            }
            Panel {
                Layout.fillWidth: true
                divider: true
                title: "Storm status"
                Body {
                    font.pixelSize: screen.active ? 23 : 18
                    text: screen.active ? "Solar storm in progress."
                        : screen.d.storm.phase === "passed" ? "Last storm has passed. Dose in shelter: " + screen.d.storm.shelter_dose_msv + " mSv. With no shelter: " + screen.d.storm.unsheltered_dose_msv + " mSv."
                        : "The solar monitor shows no storm."
                }
                Canvas {
                    id: trace
                    visible: screen.d.storm.phase !== "none"
                    Layout.fillWidth: true
                    Layout.preferredHeight: 120
                    Accessible.role: Accessible.Graphic
                    Accessible.name: "Dose rate by hour during the storm, with and without the shelter."
                    Connections { target: screen; function onDChanged() { trace.requestPaint() } }
                    onWidthChanged: requestPaint()
                    onPaint: {
                        var c = getContext("2d")
                        c.reset()
                        var s = screen.d.storm
                        if (!s.hourly) return
                        var top = Math.max.apply(null, s.hourly_free)
                        function line(data, color, dash) {
                            c.strokeStyle = color; c.lineWidth = 2; c.setLineDash(dash)
                            c.beginPath()
                            data.forEach(function (v, i) { var x = i / (data.length - 1) * width, y = height - 26 - v / top * (height - 34); i ? c.lineTo(x, y) : c.moveTo(x, y) })
                            c.stroke()
                        }
                        line(s.hourly_free, Theme.band, [2, 5])
                        line(s.hourly, Theme.ink, [])
                        c.setLineDash([]); c.fillStyle = Theme.ink2; c.font = "16px '" + Theme.body + "'"
                        c.fillText("Solid: your dosimeter. Dotted: no shelter.", 0, height - 4)
                    }
                }
            }
            Note { text: vigil.isDemo ? "The limit and dose figures are approximate and still need checking against sources. The storm size and shelter factor are made up." : "The limit is approximate and still needs checking against sources." }
            second: [
                Panel { Layout.fillWidth: true; visible: screen.active; surface: true; title: "Shelter steps"; ShelterFlow { Layout.fillWidth: true; storm: screen.d.storm } },
                Panel { Layout.fillWidth: true; visible: !screen.active && screen.drill; surface: true; title: "Storm drill"; ShelterFlow { Layout.fillWidth: true; drill: true } },
                Panel { Layout.fillWidth: true; visible: !screen.active && !screen.drill; surface: true; title: "Practice"; Body { text: "A drill walks through the shelter steps with a timer." } }
            ]
        }
    }
}
