function Serial() {
    this.buffer = "";
    this.contents = "";
    this.addChar = function(character) {
        this.buffer += character;
        this.contents += character;
    };
    this.delChar = function() {
        if(this.buffer.length > 0) {
            this.buffer = this.buffer.substring(0, this.buffer.length - 1);
            this.contents = this.contents.substring(0, this.contents.length - 1);
        }
    };
    this.newline = function() {
        this.contents += '<br />';
        this.buffer = '';
    };
    return this;
}

function init(tty) {
    var term = document.getElementById("console");
    function evt(e) {
        var code = e.keyCode;
        if(code == 13) {
            tty.newline();
        } else {
            tty.addChar(String.fromCharCode(code));
        }
        term.innerHTML = tty.contents;
        term.scrollTop = term.scrollHeight;
    }

    function backspace(e) {
        if(e.keyCode == 8) {
            tty.delChar();
        }
        term.innerHTML = tty.contents;
        term.scrollTop = term.scrollHeight;
    }
    document.onkeypress = evt;
    document.onkeydown = backspace;
}

var active_term = Serial();
