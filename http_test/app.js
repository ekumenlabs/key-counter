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

var collected_ = {};
function getCollected () {
  var clone = {};
  for (k in collected_) {
    if (collected_.hasOwnProperty(k)) {
      clone[k] = collected_[k];
    }
  }
  return clone;
}
function resetCollected (newCollected) {
  collected_ = newCollected;
  // for (k in newCollected) {
  //   if (newCollected.hasOwnProperty(k)) {
  //     collected_[k] = newCollected[k];
  //   }
  // }
}

// Collect data as it comes
app.post('/counts', function (req, res) {
  var user, value, collected = getCollected();
  for (var i = 0; i < req.body.length; i++) {
    if (allowedUserData.indexOf(req.body[i].username) != -1) {
      user = req.body[i].username;
      value = req.body[i].count;

      collected[user] = collected[user] || [];
      collected[user].push(value);
    }
  }
  // Set the collected values for the app to see.
  resetCollected(collected);
  // Answer to key_counter_server.
  res.send(202, 'Accepted');
});

var PUSH_INTERVAL = 5000;
setInterval(function () {
  var collected, value, data = [];

  // Get a copy of the currently collected counts.
  collected = getCollected();
  // Reset the collected values.
  resetCollected({});

  // Reformat the collected data.
  for (user in collected) {
    // Average the collected counts.
    for (var i = 0, value = 0; i < collected[user].length; i++) {
      value = value + collected[user][i];
    }
    data.push({username: user, count: value / collected[user].length});
  }
  // Emit to connected clients to update their counts.
  io.of('/key-count').emit('users update', data);
}, PUSH_INTERVAL);
