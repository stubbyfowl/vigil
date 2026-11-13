import QtQuick
import QtQuick.Layouts

// A city built from the check-in's food answers: fiber builds it, processed food sends in raccoons.
Item {
    id: screen
    readonly property var d: Api.ask("gut_city", { id: vigil.astronaut, day: vigil.day, v: vigil.version })
    readonly property var tiles: d.tiles || []
    readonly property var raccoonWord: ({ none: "None", low: "Low", high: "High" })

    PageScroll {
        anchors.fill: parent
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            BackButton {}
            BigTitle { text: "Gut City" }
            Placard { text: "Last " + (screen.d.days || 28) + " days" }
            Item { Layout.fillWidth: true }
            VButton { text: "Check in"; onClicked: vigil.navigate("/checkin") }
        }
        Banner { tone: "error"; text: screen.d.error || "" }
        Banner { visible: screen.d.answered_days === 0; text: "Nothing built yet. Answer the two food questions in the check-in, fiber and processed food, to start the city." }

        Split {
            Layout.fillWidth: true
            Panel {
                Layout.fillWidth: true
                surface: true
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 24
                    Repeater {
                        model: [["Population", (screen.d.population || 0).toLocaleString(Qt.locale("en_US"), "f", 0)],
                                ["Raccoon activity", screen.raccoonWord[screen.d.raccoons] || "None"],
                                ["Days answered", screen.d.answered_days || 0]]
                        ColumnLayout {
                            required property var modelData
                            spacing: 2
                            Placard { text: modelData[0] }
                            Text { text: String(modelData[1]); font.family: Theme.display; font.weight: Font.ExtraBold; font.pixelSize: 30; color: Theme.ink }
                        }
                    }
                }
                Canvas {
                    id: city
                    Layout.fillWidth: true
                    Layout.preferredHeight: width * 5 / 8
                    Accessible.role: Accessible.Graphic
                    Accessible.name: "Gut City with " + screen.tiles.filter(function (t) { return !t.trashed }).length + " standing blocks and "
                                     + screen.tiles.filter(function (t) { return t.trashed }).length + " trashed by raccoons"
                    onPaint: {
                        var c = getContext("2d")
                        c.reset()
                        var cols = screen.d.width || 8, rows = screen.d.height || 5
                        var cw = width / cols, ch = height / rows
                        c.fillStyle = Theme.panel2
                        c.fillRect(0, 0, width, height)
                        c.strokeStyle = Theme.rule
                        c.lineWidth = 1
                        for (var gx = 0; gx <= cols; gx++) { c.beginPath(); c.moveTo(gx * cw, 0); c.lineTo(gx * cw, height); c.stroke() }
                        for (var gy = 0; gy <= rows; gy++) { c.beginPath(); c.moveTo(0, gy * ch); c.lineTo(width, gy * ch); c.stroke() }
                        function raccoon(x, y, s) {
                            c.fillStyle = Theme.ink2
                            c.beginPath(); c.arc(x - s * 0.55, y - s * 0.55, s * 0.32, 0, 2 * Math.PI); c.arc(x + s * 0.55, y - s * 0.55, s * 0.32, 0, 2 * Math.PI); c.fill()
                            c.beginPath(); c.arc(x, y, s * 0.75, 0, 2 * Math.PI); c.fill()
                            c.fillStyle = Theme.bg
                            c.fillRect(x - s * 0.7, y - s * 0.22, s * 1.4, s * 0.3)
                            c.fillStyle = Theme.ink
                            c.beginPath(); c.arc(x - s * 0.3, y - s * 0.08, s * 0.1, 0, 2 * Math.PI); c.arc(x + s * 0.3, y - s * 0.08, s * 0.1, 0, 2 * Math.PI); c.fill()
                        }
                        var used = {}
                        for (var i = 0; i < screen.tiles.length; i++) {
                            var t = screen.tiles[i], x = t.x * cw, y = t.y * ch
                            used[t.x + "," + t.y] = true
                            c.save()
                            c.translate(x, y)
                            if (t.trashed) {
                                c.strokeStyle = Theme.ink2; c.lineWidth = 2
                                c.save(); c.translate(cw * 0.3, ch * 0.7); c.rotate(-0.5); c.strokeRect(-cw * 0.1, -ch * 0.2, cw * 0.2, ch * 0.3); c.restore()
                                raccoon(cw * 0.66, ch * 0.55, Math.min(cw, ch) * 0.16)
                            } else if (t.kind === "houses") {
                                c.fillStyle = Theme.ink; c.strokeStyle = Theme.ink; c.lineWidth = 2
                                for (var h = 0; h < 3; h++) {
                                    var hx = cw * (0.15 + h * 0.25), hy = ch * 0.55, hw = cw * 0.18
                                    c.strokeRect(hx, hy, hw, ch * 0.28)
                                    c.beginPath(); c.moveTo(hx - 2, hy); c.lineTo(hx + hw / 2, hy - ch * 0.16); c.lineTo(hx + hw + 2, hy); c.closePath(); c.fill()
                                }
                            } else if (t.kind === "park") {
                                c.strokeStyle = Theme.ink; c.lineWidth = 2
                                for (var p = 0; p < 3; p++) {
                                    var px = cw * (0.25 + p * 0.25), py = ch * (p === 1 ? 0.42 : 0.55)
                                    c.beginPath(); c.arc(px, py, Math.min(cw, ch) * 0.13, 0, 2 * Math.PI); c.stroke()
                                    c.beginPath(); c.moveTo(px, py + Math.min(cw, ch) * 0.13); c.lineTo(px, py + ch * 0.25); c.stroke()
                                }
                            } else {
                                c.fillStyle = Theme.ink
                                c.fillRect(cw * 0.35, ch * 0.12, cw * 0.3, ch * 0.76)
                                c.fillStyle = Theme.panel2
                                for (var r = 0; r < 5; r++) for (var k = 0; k < 2; k++) c.fillRect(cw * (0.4 + k * 0.12), ch * (0.2 + r * 0.13), cw * 0.06, ch * 0.06)
                            }
                            c.restore()
                        }
                        // Raccoons roam empty lots when processed food has been high this week.
                        var roaming = screen.d.raccoons === "high" ? 3 : screen.d.raccoons === "low" ? 1 : 0
                        for (var e = cols * rows - 1; e >= 0 && roaming > 0; e -= 7) {
                            var ex = e % cols, ey = Math.floor(e / cols)
                            if (used[ex + "," + ey]) continue
                            raccoon(ex * cw + cw / 2, ey * ch + ch / 2, Math.min(cw, ch) * 0.16)
                            roaming -= 1
                        }
                    }
                    Connections { target: screen; function onDChanged() { city.requestPaint() } }
                    Connections { target: Theme; function onModeChanged() { city.requestPaint() } }
                    onWidthChanged: requestPaint()
                }
                Note { text: "Houses: 3 servings of fiber. Park: 4. Tower: 5. A raccoon gang trashes the newest block on a day with 3 or more servings of processed food, unless fiber was 4 or more that day." }
            }
            second: [
                Panel {
                    Layout.fillWidth: true
                    surface: true
                    title: "City news"
                    Banner { visible: (screen.d.events || []).length === 0; text: "No news yet." }
                    Repeater {
                        model: screen.d.events || []
                        Body { required property string modelData; text: modelData }
                    }
                }
            ]
        }
        Note {
            Layout.maximumWidth: 900
            text: "Gut City is a game built from what you report eating in the check-in. It does not measure your microbiome, and Vigil does not read gut test kits yet."
        }
    }
}
