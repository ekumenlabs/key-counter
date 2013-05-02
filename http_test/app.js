var express = require('express')
  , io = require('socket.io')

  , app = express()
  , server = require('http').createServer(app)
  , io = io.listen(server);

// The socket.io server.
server.listen(8000);
console.log('socket.io server listening on port 8000');

app.listen(3000);
console.log('application server listening on port 3000');

///////////////////////////////////////////////////////////////////////////////

app.use(express.static(__dirname));
app.use(express.bodyParser());

var allowedUserData = ['etoccalino'];

app.post('/counts', function (req, res) {
  // console.log('body: ' + JSON.stringify(req.body));
  var collected = [];

  collected = req.body;
  // for (int i = 0; i < req.body; i++) {
  //   var user = req.body[i].user
  //     , count = req.body[i].count;

  //   if (allowedUserData.indexOf(user) == -1) {
  //     console.log('Data for user ' + user + ' is not allowed.');
  //     res.send(400, 'Bad Request');
  //   }
  //   collected.push({username: user, count: count});
  // }

  // Responde to key_counter_server.
  res.send(202, 'Accepted');

  // Emit to connected clients to update their counts.
  io.of('/key-count').emit('users update', collected);
});
