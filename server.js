const express = require('express');
const path = require('path');
const app = express();
const PORT = process.env.PORT || 5000;

// Middlewares
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Base de datos temporal en memoria para los pedidos de hielo
let pedidos = [];

// Endpoint de verificación
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'API de Pedidos de Hielo en Node.js funcionando' });
});

// GET: Obtener todos los pedidos
app.get('/api/pedidos', (req, res) => {
  res.json(pedidos);
});

// POST: Crear un nuevo pedido
app.post('/api/pedidos', (req, res) => {
  const { cliente, producto, cantidad, direccion } = req.body;
  
  if (!cliente || !producto || !cantidad) {
    return res.status(400).json({ error: 'Faltan campos obligatorios' });
  }

  const nuevoPedido = {
    id: Date.now(),
    cliente,
    producto,
    cantidad,
    direccion: direccion || 'Sin dirección',
    estado: 'Pendiente',
    fecha: new Date().toISOString()
  };

  pedidos.push(nuevoPedido);
  res.status(201).json({ message: 'Pedido creado exitosamente', pedido: nuevoPedido });
});

app.listen(PORT, () => {
  console.log(`Servidor corriendo en el puerto ${PORT}`);
});