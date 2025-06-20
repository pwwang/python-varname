function flush() {
  var id = location.hash.replace(/\./g, "\\.")
  if (id.length) {
    console.log(id);
	  // $("" + id).css("background-color","#9f9");
  }
}

// $(flush);
document.body.onload = flush;

// $("html").click(flush)
