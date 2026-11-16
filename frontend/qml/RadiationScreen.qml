import QtQuick
import QtQuick.Layouts

Item {
    id: screen
    readonly property var weather: Api.ask("space_weather", {})
    readonly property var d: Api.ask("radiation", { id: vigil.astronaut, day: vigil.day, v: vigil.version })
    readonly property bool active: d.storm.phase === "active"
    property bool drill: false
    function pct(v) { return v === null ? 0 : Math.min(v / d.limit_msv, 1) }

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
            detail: screen.d.projected_total_msv === null ? "Log personal dosimeter readings to see where the mission total is heading."
                    : "At this rate it will be " + screen.d.projected_total_msv + " mSv when the mission ends."
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 8
            Item {
                id: track
                Layout.fillWidth: true
                implicitHeight: 18
                Accessible.role: Accessible.ProgressBar
                Accessible.name: "Career dose " + screen.d.career_dose_msv + " of " + screen.d.limit_msv + " millisieverts." + (screen.d.projected_total_msv === null ? "" : " Projected " + screen.d.projected_total_msv + ".")
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
                // Which real storm this replays, and its dose against NASA's per-event limit [V1 4031].
                Note {
                    visible: !!screen.d.storm.event_begin
                    text: screen.d.storm.event_begin ? "Replays the solar proton event of " + new Date(screen.d.storm.event_begin.replace("Z", ":00Z")).toLocaleDateString(Qt.locale("en_GB"), "d MMMM yyyy")
                        + " from NOAA's list, peak " + Number(screen.d.storm.event_peak_pfu).toLocaleString(Qt.locale("en_US"), "f", 0) + " pfu above 10 MeV. Turning flux into dose here is a team assumption." : ""
                }
                ColumnLayout {
                    visible: screen.d.storm.event_limit_msv !== undefined
                    Layout.fillWidth: true
                    spacing: 6
                    RowLayout {
                        Layout.fillWidth: true
                        Placard { text: "This storm, in shelter"; Layout.fillWidth: true }
                        Text {
                            text: (screen.d.storm.shelter_dose_msv || 0) + " of " + screen.d.storm.event_limit_msv + " mSv"
                            font.family: Theme.display; font.weight: Font.DemiBold; font.pixelSize: 17; font.features: { "tnum": 1 }; color: Theme.ink
                        }
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 6
                        color: Theme.panel2
                        Rectangle { width: parent.width * Math.min(1, (screen.d.storm.shelter_dose_msv || 0) / (screen.d.storm.event_limit_msv || 250)); height: parent.height; color: Theme.caution }
                        Accessible.role: Accessible.ProgressBar
                        Accessible.name: "Storm dose " + (screen.d.storm.shelter_dose_msv || 0) + " of the " + screen.d.storm.event_limit_msv + " millisievert per-storm limit"
                    }
                    Note { text: "NASA holds each solar particle event under 250 mSv (NASA-STD-3001, V1 4031)." }
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
            Note { text: vigil.isDemo ? "Limits are from NASA-STD-3001. The storm replays a real event from NOAA's list. How its proton flux becomes dose in this ship, and how much the shelter blocks, are team assumptions." : "Limits are from NASA-STD-3001. Dose comes from the readings your crew logs." }
            second: [
                Panel { Layout.fillWidth: true; visible: screen.active; surface: true; title: "Shelter steps"; ShelterFlow { Layout.fillWidth: true; storm: screen.d.storm } },
                Panel { Layout.fillWidth: true; visible: !screen.active && screen.drill; surface: true; title: "Storm drill"; ShelterFlow { Layout.fillWidth: true; drill: true } },
                Panel { Layout.fillWidth: true; visible: !screen.active && !screen.drill; surface: true; title: "Practice"; Body { text: "A drill walks through the shelter steps with a timer." } },
                // NASA's own record of solar particle storms, bundled so Vigil stays offline.
                Panel {
                    Layout.fillWidth: true
                    visible: !!screen.weather.available
                    surface: true
                    title: "Solar storms measured, NASA DONKI"
                    Body { text: screen.weather.available ? screen.weather.storms + " solar particle storms measured by spacecraft instruments from " + screen.weather.first + " to " + screen.weather.last + ". They rise and fall with the Sun's 11-year cycle." : "" }
                    // Storms per year: one bar per year, its height the count. Point at or tap a bar to read it.
                    Item {
                        id: chart
                        Layout.fillWidth: true
                        Layout.preferredHeight: 160
                        property int picked: -1
                        readonly property var years: screen.weather.per_year || []
                        readonly property real slot: width / Math.max(1, years.length)
                        Repeater {
                            model: chart.years
                            Item {
                                id: bar
                                required property var modelData
                                required property int index
                                readonly property bool peak: modelData.storms === screen.weather.most
                                x: index * chart.slot
                                width: chart.slot
                                height: chart.height
                                Accessible.role: Accessible.StaticText
                                Accessible.name: modelData.year + ": " + modelData.storms + (modelData.storms === 1 ? " storm" : " storms")
                                Rectangle {
                                    id: fill
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    anchors.bottom: yr.top
                                    anchors.bottomMargin: 6
                                    width: Math.max(4, chart.slot - 6)
                                    height: Math.max(bar.modelData.storms ? 3 : 1, (parent.height - 44) * bar.modelData.storms / Math.max(1, screen.weather.most))
                                    radius: 2
                                    color: chart.picked === bar.index ? Theme.ink : Theme.link
                                }
                                Text { visible: bar.peak || chart.picked === bar.index; anchors.bottom: fill.top; anchors.bottomMargin: 2; anchors.horizontalCenter: parent.horizontalCenter; text: bar.modelData.storms; font.family: Theme.mono; font.pixelSize: 12; color: Theme.ink }
                                Text { id: yr; anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter; text: "'" + String(bar.modelData.year).slice(2); font.family: Theme.mono; font.pixelSize: 11; color: Theme.ink2 }
                                MouseArea { anchors.fill: parent; hoverEnabled: true; onEntered: chart.picked = bar.index; onExited: chart.picked = -1; onClicked: chart.picked = bar.index }
                            }
                        }
                    }
                    Note { text: chart.picked >= 0 ? chart.years[chart.picked].year + ": " + chart.years[chart.picked].storms + " storms measured." : "Storms per year, with 2026 up to the day the data was fetched. Point at a bar to read its year." }
                    Placard { text: "Most recent" }
                    Repeater {
                        model: screen.weather.recent || []
                        RowLayout {
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: 12
                            Text { text: modelData.date; font.family: Theme.mono; font.pixelSize: 14; color: Theme.ink }
                            Note { Layout.fillWidth: true; text: (modelData.flare ? "After a solar flare, seen by " : modelData.cme ? "After a coronal mass ejection, seen by " : "Seen by ") + modelData.instruments[0].split(":")[0] + (modelData.instruments.length > 1 ? " and " + (modelData.instruments.length - 1) + " more" : "") }
                        }
                    }
                    Note { text: "From NASA's Space Weather Database Of Notifications, Knowledge, Information (DONKI), retrieved " + (screen.weather.retrieved || "") + ". Its " + (screen.weather.entries || 0) + " entries are grouped by the flare or eruption they share, and model forecasts are left out." }
                }
            ]
        }
    }
}
