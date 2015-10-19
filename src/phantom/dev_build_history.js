var casper = require('casper').create({
    verbose: true,
    logLevel: "info",

    viewportSize: {
      width: 1920,
      height: 1080
    }
});
casper.options.waitTimeout = 10000; // milliseconds
var x = require("casper").selectXPath;

var dockerhub_user = "fedorainfratesting";
// casper.cli.get("dockerhub_user");
var repo_name = "vgologuz-test2";
//casper.cli.get("repo_name");
var url  = 'https://hub.docker.com/r/' + dockerhub_user +'/' + repo_name + '/builds/';

casper.start(url, function(){
    this.clickLabel('Build Details');
    this.echo("url: " + url);
//    this.debugPage();

});



casper.then(function() {
    // very dirty, easily fail if dockerhub change layout

//    casper.captureSelector("table.png", ".repo-details-blank table");
//
//    var selector = "(//table//tbody//tr)//td";


    var sel = x("//table//a");
    casper.captureSelector("table.png", sel);

    require('utils').dump(casper.getElementsAttribute(sel, 'href'));



//    var result = this.evaluate(function(){
//        var chunks = [];
////        var table = document.querySelector('table.table:nth-child(4)');
//        var table = document.querySelector(".repo-details-blank table");
//        console.log("table: ");
//        console.log(table);
//        var children = table.querySelector("tbody").childNodes;
//
//        for(i=0; i < children.length; i++){
//            var node = children[i];
//            var chunk = {};
//            var td_list = node.querySelectorAll("td");
//            chunk["build_id"] = td_list[0].textContent;
//            chunk["status"] = td_list[1].textContent;
//            chunk["created_on"] = td_list[2].attributes['utc-date'].value;
//            chunk["updated_on"] = td_list[3].attributes['utc-date'].value;
//            chunks.push(chunk);
//        }
//        return chunks;
//    });
//    this.echo(JSON.stringify(result));


//    casper.wait(5900);
});

casper.run();
