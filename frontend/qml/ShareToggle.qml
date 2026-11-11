Toggle {
    id: toggle
    property string audience: ""
    property string field: "share_crew"
    text: "Share my raw readings with " + audience
    checked: Api.ask("get_share", { id: vigil.astronaut })[field]
    onToggled: {
        var args = { id: vigil.astronaut }
        args[field] = checked
        Api.ask("set_share", args)
    }
}
