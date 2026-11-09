import QtQuick
import QtQuick.Layouts

ColumnLayout {
    BigTitle { text: "That screen does not exist."; Layout.alignment: Qt.AlignHCenter }
    VButton { text: "Go home"; Layout.alignment: Qt.AlignHCenter; onClicked: vigil.navigate("/") }
    Item { Layout.fillHeight: true }
}
