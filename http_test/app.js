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

allowedUserData = ['etoccalino'];

app.post('/:username', function (req, res) {
  user = req.params.username;

  if (allowedUserData.indexOf(user) == -1) {

    console.log('Data for user ' + user + ' is not allowed.');
    res.send(400, 'Bad Request');

  } else if (req.body.count === undefined) {

    console.log('Data for user ' + user + ' does not have a "count" value');
    res.send(400, 'Bad Request');

  }
  else {

    // Responde to key_counter_server.
    console.log(user + ': ' + req.body.count);
    res.send(202, 'Accepted');

    // Emit to connected clients to update their counts.
    io.of('/key-count').emit('user update', {user: user, count: req.body.count});

  }
});
