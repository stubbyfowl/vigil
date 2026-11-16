import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// The body map: tap a part of the body to see what it does, which of NASA's five hazards reach it,
// its readings against your normal, and how to measure and act on each one.
Item {
    id: screen
    readonly property var d: Api.ask("body_map", { id: vigil.astronaut, day: vigil.day, v: vigil.version })
    readonly property var regions: d.regions || []
    property string selected: "heart"
    property string hazard: ""
    property string open: ""
    readonly property var region: regions.find(function (r) { return r.id === screen.selected }) || null
    readonly property var hazardInfo: (d.hazards || []).find(function (h) { return h.id === screen.hazard }) || null
    readonly property var hazardNames: {
        var out = {}
        ;(d.hazards || []).forEach(function (h) { out[h.id] = h.name })
        return out
    }
    function word(status) { return status === "none" ? "No baseline yet" : Theme.statusWord(status) }
    function tone(status) { return status === "none" ? Theme.ink2 : Theme.statusColor(status) }
    function touched(r) { return screen.hazard === "" || r.hazards.indexOf(screen.hazard) >= 0 }

    PageScroll {
        anchors.fill: parent
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            BackButton {}
            BigTitle { text: "Your body" }
            Placard { text: "Day " + (screen.d.day || "") + "  ·  " + (screen.d.tracked || 0) + " readings" }
            Item { Layout.fillWidth: true }
        }
        Banner { tone: "error"; text: screen.d.error || "" }
        Note {
            Layout.maximumWidth: 980
            text: "Tap a part of the body for its readings and what to do. The five buttons are the hazards of human spaceflight from NASA's Human Research Program: choose one to see which parts of the body it reaches."
        }
        Flow {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: screen.d.hazards || []
                VButton {
                    required property var modelData
                    text: modelData.name
                    selected: screen.hazard === modelData.id
                    onClicked: screen.hazard = screen.hazard === modelData.id ? "" : modelData.id
                }
            }
        }
        Banner {
            visible: !!screen.hazardInfo
            text: screen.hazardInfo ? "NASA: " + screen.hazardInfo.nasa + "  Vigil watches: " + screen.hazardInfo.vigil : ""
        }

        Split {
            Layout.fillWidth: true
            stackBelow: 1000
            Panel {
                Layout.fillWidth: true
                surface: true
                Item {
                    id: stage
                    Layout.fillWidth: true
                    Layout.preferredHeight: 600
                    readonly property real figureW: Math.min(width * 0.34, 270)
                    readonly property real edge: (width - figureW) / 2
                    function px(r) { return Qt.point(stage.edge + r.x * figureW, r.y * height) }

                    // A plain figure, drawn as rounded strokes, with a line from each part to its label.
                    Canvas {
                        id: figure
                        anchors.fill: parent
                        Accessible.role: Accessible.Graphic
                        Accessible.name: "Human figure with " + screen.regions.length + " parts of the body to choose from"
                        onPaint: {
                            var c = getContext("2d")
                            c.reset()
                            var w = stage.figureW, h = height, x0 = stage.edge
                            function P(x, y) { return [x0 + x * w, y * h] }
                            c.lineCap = "round"
                            c.lineJoin = "round"
                            var limbs = [[[0.5, 0.13], [0.5, 0.2]], [[0.27, 0.2], [0.73, 0.2]], [[0.27, 0.21], [0.15, 0.42], [0.11, 0.6]],
                                         [[0.73, 0.21], [0.85, 0.42], [0.89, 0.6]], [[0.4, 0.5], [0.37, 0.75], [0.35, 0.97]], [[0.6, 0.5], [0.63, 0.75], [0.65, 0.97]]]
                            for (var pass = 0; pass < 2; pass++) {
                                c.strokeStyle = pass === 0 ? Theme.rule : Theme.panel2
                                c.fillStyle = c.strokeStyle
                                var grow = pass === 0 ? 4 : 0
                                c.lineWidth = w * 0.13 + grow
                                for (var i = 0; i < limbs.length; i++) {
                                    c.beginPath()
                                    var p0 = P(limbs[i][0][0], limbs[i][0][1])
                                    c.moveTo(p0[0], p0[1])
                                    for (var j = 1; j < limbs[i].length; j++) { var pj = P(limbs[i][j][0], limbs[i][j][1]); c.lineTo(pj[0], pj[1]) }
                                    c.stroke()
                                }
                                c.beginPath()
                                var tl = P(0.29, 0.2), br = P(0.71, 0.52)
                                c.roundedRect(tl[0] - grow / 2, tl[1] - grow / 2, br[0] - tl[0] + grow, br[1] - tl[1] + grow, w * 0.12, w * 0.12)
                                c.fill()
                                c.beginPath()
                                var head = P(0.5, 0.07)
                                c.arc(head[0], head[1], w * 0.12 + grow / 2, 0, 2 * Math.PI)
                                c.fill()
                            }
                            // Leader lines from each part to its label.
                            c.lineWidth = 1.2
                            for (var k = 0; k < screen.regions.length; k++) {
                                var r = screen.regions[k]
                                var at = stage.px(r)
                                var toRight = r.x >= 0.5
                                c.strokeStyle = screen.touched(r) ? Theme.ink2 : Theme.rule
                                c.beginPath()
                                c.moveTo(at.x, at.y)
                                c.lineTo(toRight ? stage.edge + stage.figureW + 24 : stage.edge - 24, at.y)
                                c.stroke()
                            }
                        }
                        Connections { target: screen; function onRegionsChanged() { figure.requestPaint() } function onHazardChanged() { figure.requestPaint() } }
                        Connections { target: Theme; function onModeChanged() { figure.requestPaint() } }
                        onWidthChanged: requestPaint()
                    }

                    Repeater {
                        model: screen.regions
                        Item {
                            id: spot
                            required property var modelData
                            readonly property point at: stage.px(modelData)
                            readonly property bool toRight: modelData.x >= 0.5
                            readonly property bool chosen: screen.selected === modelData.id
                            anchors.fill: parent
                            opacity: screen.touched(modelData) ? 1 : 0.35
                            // The point on the body.
                            AbstractButton {
                                x: spot.at.x - width / 2
                                y: spot.at.y - height / 2
                                width: Theme.touch
                                height: Theme.touch
                                focusPolicy: Qt.StrongFocus
                                Accessible.name: spot.modelData.name + ", " + screen.word(spot.modelData.status)
                                onClicked: { screen.selected = spot.modelData.id; screen.open = "" }
                                background: Item {
                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: spot.chosen ? 34 : 24
                                        height: width
                                        radius: width / 2
                                        color: Theme.panel
                                        border.width: 3
                                        border.color: screen.tone(spot.modelData.status)
                                        Rectangle { anchors.centerIn: parent; width: 8; height: 8; radius: 4; color: screen.tone(spot.modelData.status) }
                                    }
                                }
                            }
                            // Its label, with the status in words.
                            AbstractButton {
                                id: callout
                                x: spot.toRight ? stage.edge + stage.figureW + 24 : stage.edge - 24 - width
                                y: spot.at.y - height / 2
                                width: Math.min(230, stage.edge - 30)
                                height: Theme.touch
                                focusPolicy: Qt.StrongFocus
                                Accessible.name: spot.modelData.name + ", " + screen.word(spot.modelData.status) + ". Show details."
                                onClicked: { screen.selected = spot.modelData.id; screen.open = "" }
                                background: Rectangle {
                                    radius: Theme.controlRadius
                                    color: spot.chosen ? Theme.panel2 : "transparent"
                                    border.width: callout.visualFocus || spot.chosen ? 2 : 1
                                    border.color: callout.visualFocus ? Theme.link : spot.chosen ? Theme.ink2 : Theme.rule
                                }
                                contentItem: Column {
                                    leftPadding: 12
                                    rightPadding: 12
                                    topPadding: 7
                                    Text { text: spot.modelData.name; width: callout.width - 24; fontSizeMode: Text.HorizontalFit; minimumPixelSize: 11; font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 15; color: Theme.ink }
                                    Text { text: screen.word(spot.modelData.status).toUpperCase(); font.family: Theme.mono; font.pixelSize: 11; font.letterSpacing: 1.6; color: screen.tone(spot.modelData.status) }
                                }
                            }
                        }
                    }
                }
            }
            second: [
                Panel {
                    Layout.fillWidth: true
                    surface: true
                    visible: !!screen.region
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Text { Layout.fillWidth: true; text: screen.region ? screen.region.name : ""; wrapMode: Text.WordWrap; font.family: Theme.display; font.weight: Font.ExtraBold; font.pixelSize: 28; color: Theme.ink }
                        StatusPill { visible: !!screen.region && screen.region.status !== "none"; status: screen.region ? screen.region.status : "green" }
                    }
                    Body { text: screen.region ? screen.region.function : "" }
                    Placard { text: "NASA hazards that reach it" }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Repeater {
                            model: screen.region ? screen.region.hazards : []
                            Rectangle {
                                required property string modelData
                                implicitWidth: hz.implicitWidth + 20
                                implicitHeight: 30
                                radius: 2
                                color: "transparent"
                                border.color: Theme.rule
                                Placard { id: hz; anchors.centerIn: parent; text: screen.hazardNames[modelData] || modelData; color: Theme.ink }
                            }
                        }
                    }
                    Placard { text: "NASA Human Research Program risks" }
                    Repeater {
                        model: screen.region ? screen.region.risks : []
                        Note { required property string modelData; text: modelData }
                    }
                    Placard { text: "Readings  ·  tap one for how to measure and what to do" }
                    Repeater {
                        model: screen.region ? screen.region.readings : []
                        ColumnLayout {
                            id: reading
                            required property var modelData
                            readonly property bool expanded: screen.open === modelData.id
                            Layout.fillWidth: true
                            spacing: 6
                            AbstractButton {
                                Layout.fillWidth: true
                                implicitHeight: Theme.touch
                                focusPolicy: Qt.StrongFocus
                                Accessible.name: reading.modelData.name + ", " + (reading.modelData.value === null ? "no reading" : reading.modelData.value + " " + reading.modelData.unit) + ", " + reading.modelData.word
                                onClicked: screen.open = reading.expanded ? "" : reading.modelData.id
                                background: Rectangle { color: reading.expanded ? Theme.panel2 : "transparent"; radius: Theme.controlRadius; border.width: parent.visualFocus ? 2 : 0; border.color: Theme.link }
                                contentItem: RowLayout {
                                    spacing: 12
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Layout.leftMargin: 8
                                        spacing: 0
                                        Text { text: reading.modelData.name; font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 16; color: Theme.ink }
                                        Text { text: reading.modelData.range; font.family: Theme.body; font.pixelSize: 13; color: Theme.ink2 }
                                    }
                                    Text {
                                        text: reading.modelData.value === null ? "--" : Theme.amount(reading.modelData.value, reading.modelData.unit)
                                        font.family: Theme.body; font.weight: Font.DemiBold; font.pixelSize: 18; font.features: { "tnum": 1 }; color: Theme.ink
                                    }
                                    Text {
                                        Layout.preferredWidth: 170
                                        Layout.rightMargin: 8
                                        horizontalAlignment: Text.AlignRight
                                        wrapMode: Text.WordWrap
                                        text: reading.modelData.word
                                        font.family: Theme.mono; font.pixelSize: 12; font.letterSpacing: 0.8; font.capitalization: Font.AllUppercase
                                        color: screen.tone(reading.modelData.status)
                                    }
                                }
                            }
                            ColumnLayout {
                                visible: reading.expanded
                                Layout.fillWidth: true
                                Layout.leftMargin: 8
                                Layout.rightMargin: 8
                                spacing: 6
                                Repeater {
                                    model: [["How to measure", "measure"], ["Why it matters in space", "why"], ["What to do", "act"]]
                                    ColumnLayout {
                                        required property var modelData
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Placard { text: modelData[0] }
                                        Body { text: reading.modelData.guide[modelData[1]] || "" }
                                    }
                                }
                            }
                            Rectangle { Layout.fillWidth: true; height: 1; color: Theme.rule }
                        }
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Repeater {
                            model: screen.region ? screen.region.links : []
                            VButton { required property var modelData; text: modelData[1]; onClicked: vigil.navigate(modelData[0]) }
                        }
                    }
                }
            ]
        }
        Note {
            Layout.maximumWidth: 980
            text: "Hazards and risks are from NASA's Human Research Program. Blood sugar ranges are from the CDC, and the cabin CO2 limit is from NASA-STD-3001. Guidance is general and written by the team. Vigil does not diagnose. Check with your flight surgeon."
        }
    }
}
