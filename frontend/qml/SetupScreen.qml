import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Two short steps: the mission, then the first Commander. The Commander adds everyone else.
Item {
    id: screen
    objectName: "setupStage"
    property int step: 1
    property var errors: ({})
    property string failure: ""

    function today() {
        var d = new Date()
        return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0")
    }
    function nextStep() {
        var e = {}
        if (!missionName.text.trim()) e.name = "Give the mission a name."
        if (!/^\d{4}-\d{2}-\d{2}$/.test(startDate.text.trim())) e.start = "Write it as year-month-day, for example " + today() + "."
        var days = parseInt(missionLength.text)
        if (!(days >= 1 && days <= 1100)) e.length = "From 1 to 1100 days."
        errors = e
        if (Object.keys(e).length === 0) step = 2
    }
    function create() {
        var e = {}
        if (!commander.text.trim()) e.commander = "Enter the Commander's name."
        if (pin.text.length < 4) e.pin = "A PIN is 4 to 8 digits."
        else if (pin.text !== pin2.text) e.pin2 = "The two PINs do not match."
        var dose = dose_.text.trim() === "" ? 0 : Number(dose_.text)
        if (isNaN(dose) || dose < 0 || dose > 2000) e.dose = "From 0 to 2000 mSv."
        errors = e
        if (Object.keys(e).length) return
        failure = vigil.setupMission(JSON.stringify({
            name: missionName.text, start_date: startDate.text.trim(), length_days: parseInt(missionLength.text),
            commander: commander.text, pin: pin.text, prior_dose: dose
        }))
    }

    ColumnLayout {
        anchors { fill: parent; margins: Theme.gutter; topMargin: 32 }
        spacing: 16
        RowLayout {
            spacing: 12
            VButton { kind: "quiet"; text: "‹  Back"; implicitWidth: 92; onClicked: screen.step === 1 ? vigil.leaveSetup() : screen.step = 1 }
            BigTitle { text: screen.step === 1 ? "Set up a mission" : "The first Commander" }
            Placard { text: "Step " + screen.step + " of 2" }
        }
        Body {
            Layout.maximumWidth: 760
            color: Theme.ink2
            text: screen.step === 1
                  ? "Day 1 is the start date. Vigil counts mission days from it and learns each person's normal over the first days of readings."
                  : "The Commander manages accounts and reads the audit log. Each person's health data stays private to them."
        }
        ColumnLayout {
            visible: screen.step === 1
            Layout.maximumWidth: 560
            spacing: 14
            Field { id: missionName; label: "Mission name"; placeholder: "Artemis analog 1"; maxLength: 60; error: screen.errors.name || "" }
            RowLayout {
                spacing: 16
                Field { id: startDate; label: "Start date"; text: screen.today(); helper: "Today or earlier"; maxLength: 10; error: screen.errors.start || "" }
                Field { id: missionLength; label: "Length in days"; text: "180"; digits: true; maxLength: 4; error: screen.errors.length || "" }
            }
            VButton { Layout.topMargin: 8; kind: "primary"; text: "Next"; onClicked: screen.nextStep() }
        }
        ColumnLayout {
            visible: screen.step === 2
            Layout.maximumWidth: 560
            spacing: 14
            Field { id: commander; label: "Commander's full name"; maxLength: 40; error: screen.errors.commander || "" }
            Field { id: dose_; label: "Career radiation dose before this mission (mSv)"; text: "0"; helper: "Used for the radiation limit. Ask your flight surgeon."; maxLength: 6; error: screen.errors.dose || "" }
            RowLayout {
                spacing: 16
                Field { id: pin; label: "PIN"; secret: true; digits: true; maxLength: 8; helper: "4 to 8 digits"; error: screen.errors.pin || "" }
                Field { id: pin2; label: "PIN again"; secret: true; digits: true; maxLength: 8; error: screen.errors.pin2 || ""; onAccepted: screen.create() }
            }
            Banner { tone: "error"; text: screen.failure }
            VButton { Layout.topMargin: 8; kind: "primary"; text: "Create mission"; onClicked: screen.create() }
        }
        Item { Layout.fillHeight: true }
    }
}
