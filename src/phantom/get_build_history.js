var casper = require('casper').create({
//    verbose: true,
//    logLevel: "info"
});
casper.options.waitTimeout = 10000; // milliseconds

var dockerhub_user = casper.cli.get("dockerhub_user");
var repo_name = casper.cli.get("repo_name");
var url  = 'https://registry.hub.docker.com/u/' + dockerhub_user +'/' + repo_name + '/';

casper.start(url, function(){
    this.clickLabel('Build Details');
//    this.echo("url: " + url);
//    this.debugPage();

});



casper.then(function() {
    // very dirty, easily fail if dockerhub change layout
    var result = this.evaluate(function(){
        var chunks = [];
        var table = document.querySelector('table.table:nth-child(4)');
        var children = table.querySelector("tbody").childNodes;

        for(i=0; i < children.length; i++){
            var node = children[i];
            var chunk = {};
            var td_list = node.querySelectorAll("td");
            chunk["build_id"] = td_list[0].textContent;
            chunk["status"] = td_list[1].textContent;
            chunk["created_on"] = td_list[2].attributes['utc-date'].value;
            chunk["updated_on"] = td_list[3].attributes['utc-date'].value;
            chunks.push(chunk);
        }
        return chunks;
    });
    this.echo(JSON.stringify(result));
});

casper.run();
