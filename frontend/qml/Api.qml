pragma Singleton
import QtQml

QtObject {
    function ask(name, args) { return JSON.parse(vigil.ask(name, JSON.stringify(args || {}))) }
}
